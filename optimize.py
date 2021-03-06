from __future__ import print_function
import tensorflow as tf
from hyperas.distributions import choice, uniform
from hyperopt import Trials, STATUS_OK, tpe, rand
from hyperas import optim
import numpy as np

def VAE1D(train, valid, agedTrain, agedValid):
	
	from keras.callbacks import ModelCheckpoint
	from keras.models import Model
	from keras.layers import Dense, Input, Flatten, Reshape, Lambda, Conv1D, Dropout
	from keras import optimizers
	from Minerva import huber_loss
		
	early = EarlyStopping(monitor='val_mean_absolute_error', 
		min_delta=0.0001, patience=50, verbose=1, mode='min')
	saved = "./optimizedW.h5"
	checkpoint = ModelCheckpoint(saved, monitor='val_loss', verbose=0,
			save_best_only=True, mode='min',save_weights_only=True)	
	
	codeSize = {{choice([7,9,11,13,15,17,19])}}

	def sample_z(args):
		mu, log_sigma = args
		eps = K.random_normal(shape=(codeSize,),mean=0.,stddev=1.)
		return mu + K.exp(log_sigma / 2) * eps

	dim1 = {{choice([16,32,48,64,96,128,256,512])}}
	dim2 = {{choice([16,32,48,64,96,128,256,512])}}
	dim3 = {{choice([16,32,48,64,96,128,256,512])}}
	
	f1 = {{choice([3,5,7])}}
	f2 = {{choice([3,5,7])}}
	f3 = {{choice([3,5,7])}}
	
	fe = Flatten(name = "FE")
	encDrop = {{choice(['drop', 'noDrop'])}} == 'drop'
	encMore = {{choice(['more', 'less'])}} == 'more'
	
	dim4 = {{choice([16,32,48,64,96,128,256,512])}}
	dim5 = {{choice([16,32,48,64,96,128,256,512])}}
	dim6 = {{choice([16,32,48,64,96,128,256,512])}}
	
	decDrop = {{choice(['drop', 'noDrop'])}} == 'drop'
	decMore = {{choice(['more', 'less'])}} == 'more'
	
	hiddenActivation = {{choice(['linear', 'relu','tanh'])}}
	outputActivation = {{choice(['linear', 'relu','tanh'])}}
	
	batch_size = {{choice([64,128])}}
	lr = {{choice([0.00005,0.0001,0.0002])}}
	
	dropPerc =0.5
	
	### ENCODER LAYERS
	inputs = Input(shape=(20,2),name="IN")
	
	eh1 = Conv1D(dim1,f1, activation=hiddenActivation,name = "EH1")
	eh2 = Conv1D(dim2,f2, activation=hiddenActivation,name = "EH2")
	eh3 = Conv1D(dim3,f3, activation=hiddenActivation,name = "EH3")
	edrop = Dropout(dropPerc,name= "DE")
	mean = Dense(codeSize, activation  =outputActivation,name = "MU")
	logsg =  Dense(codeSize, activation=outputActivation, name = "LOG_SIGMA")
	
	
	### DECODER LAYERS
	dh1 = Dense(dim4, activation=hiddenActivation,name = "DH1")
	dh2 = Dense(dim5, activation=hiddenActivation,name = "DH2")
	dh3 = Dense(dim6, activation=hiddenActivation,name = "DH3")
	ddrop = Dropout(dropPerc,name = "DD")
	
	decoded = Dense(20*2,activation=outputActivation,name="DECODED")
	decoderOut = Reshape((20, 2),name="OUT")
	
	### MODEL

	if encMore:
		encConv = eh3(eh2(eh1((inputs))))
	else:
		encConv = eh2(eh1((inputs)))
	
	if encDrop:
		mu 		  = mean(fe(edrop(encConv)))
		log_sigma = logsg(fe(edrop(encConv)))
	else:
		mu = mean(fe(encConv))
		log_sigma = logsg(fe(encConv))
	
	z = Lambda(sample_z,name="CODE")([mu, log_sigma])
	
	if decMore:
		decConv = dh3(dh2(dh1((z))))
	else:
		decConv = dh2(dh1((z)))
	
	if decDrop:
		trainDecOut = decoderOut(decoded((ddrop(decConv))))
	else:
		trainDecOut = decoderOut(decoded((decConv)))
	

	vae = Model(inputs, trainDecOut)
	
	opt = optimizers.Adam(lr=lr) 
	saved = "./optimizedW.h5"
	checkpoint = ModelCheckpoint(saved, monitor='val_loss', verbose=0,
			save_best_only=True, mode='min',save_weights_only=True)
	
	vae.compile(loss = huber_loss,optimizer=opt,metrics=['mae'])
	
	#print(vae.summary())
	
	vae.fit(train, train,
			verbose = 0,
			batch_size=batch_size,
			epochs=300,
			validation_data=(valid,valid),
			callbacks=[checkpoint]
	)
	
	vae.load_weights(saved,by_name=True)
	
	HL_full, MAE_full = vae.evaluate(valid, valid, verbose=0)
	
	
	ydecoded = vae.predict(valid,  batch_size=100)
	maes = np.zeros(ydecoded.shape[0], dtype='float32')
	for sampleCount in range(0,ydecoded.shape[0]):
		maes[sampleCount] = mean_absolute_error(valid[sampleCount],ydecoded[sampleCount])
	
	prc = np.percentile(maes,[3,97])
	sigma = np.std(maes)
	
	score = HL_full #MAE_full + sigma + prc[1] 
	print("Score: %f Sigma: %f MAE: %f Loss: %f Perc: %f" % (score,sigma,MAE_full,HL_full, prc[1]))
	return {'loss': score, 'status': STATUS_OK, 'model': vae}

def VAE2D(train, valid, agedTrain, agedValid):
	
	from keras.callbacks import ModelCheckpoint, EarlyStopping
	from keras.models import Model
	from keras.layers import Dense, Input, Flatten, Reshape, Lambda, Conv2D, Dropout
	from keras import optimizers
	#from Minerva import huber_loss
	from Minerva import vae_loss
	
	
	early = EarlyStopping(monitor='val_mean_absolute_error', 
		min_delta=0.0001, patience=100, verbose=1, mode='min')
	
	saved = "./optimizedW.h5"
	checkpoint = ModelCheckpoint(saved, monitor='val_loss', verbose=0,
			save_best_only=True, mode='min',save_weights_only=True)	
	
	codeSize = {{choice([7,9,11,13,15,17,19])}}

	def sample_z(args):
		mu, log_sigma = args
		eps = K.random_normal(shape=(codeSize,),mean=0.,stddev=1.)
		return mu + K.exp(log_sigma / 2) * eps

	dim1 = {{choice([16,32,48,64,96,128,256,512])}}
	dim2 = {{choice([16,32,48,64,96,128,256,512])}}
	dim3 = {{choice([16,32,48,64,96,128,256,512])}}
	
	encDrop = {{choice(['drop', 'noDrop'])}} == 'drop'
	encMore = {{choice(['more', 'less'])}} == 'more'
	
	dim4 = {{choice([16,32,48,64,96,128,256,512])}}
	dim5 = {{choice([16,32,48,64,96,128,256,512])}}
	dim6 = {{choice([16,32,48,64,96,128,256,512])}}
	
	decDrop = {{choice(['drop', 'noDrop'])}} == 'drop'
	decMore = {{choice(['more', 'less'])}} == 'more'
	
	hiddenActivation = {{choice(['tanh', 'relu'])}}
	
	batch_size = 64
	lr = {{choice([0.00005,0.0001,0.0002])}}
	
	deconvDecoder = {{choice(['dense', 'deconv'])}} == 'deconv'
	
	dropPerc =0.5
	
	if(encMore):
		filterSize = 2
	else:
		filterSize = 3
	
	### ENCODER LAYERS
	inputs = Input(shape=(20,2),name="IN")
	er = Reshape((4, 5, 2),name="ER")
	eh1 = Conv2D(dim1,filterSize, activation=hiddenActivation,name = "EH1")
	eh2 = Conv2D(dim2,filterSize, activation=hiddenActivation,name = "EH2")
	eh3 = Conv2D(dim3,filterSize, activation=hiddenActivation,name = "EH3")
	fe = Flatten(name="FE")
	edrop = Dropout(dropPerc,name= "DE")
	mean = Dense(codeSize, activation='linear',name = "MU")
	logsg =  Dense(codeSize, activation='linear', name = "LOG_SIGMA")
	
	### MODEL ENCODER
	if encMore:
		encConv = eh3(eh2(eh1(er(inputs))))
	else:
		encConv = (eh1(er(inputs)))
	
	if encDrop:
		mu 		  = mean(fe(edrop(encConv)))
		log_sigma = logsg(fe(edrop(encConv)))
	else:
		mu = mean(fe(encConv))
		log_sigma = logsg(fe(encConv))
	
	z = Lambda(sample_z,name="CODE")([mu, log_sigma])
	
	### DECODER LAYERS
	ddrop = Dropout(dropPerc,name = "DD")
	decoded = Dense(20*2,activation='linear',name="DECODED")
	decoderOut = Reshape((20, 2),name="OUT")
	fd = Flatten(name="FD")
	
	### MODEL DECODER
	if(deconvDecoder):
		dr = Reshape((1,1,codeSize),name="DR")
		dh1 = Conv2DTranspose(dim4,filterSize, activation=hiddenActivation,name = "DH1")
		dh2 = Conv2DTranspose(dim5,filterSize, activation=hiddenActivation,name = "DH2")
		dh3 = Conv2DTranspose(dim6,filterSize, activation=hiddenActivation,name = "DH3")
		if decMore:
			decConv = dh3(dh2(dh1(dr(z))))
		else:
			decConv = (dh1(dr(z)))
		if decDrop:
			trainDecOut = decoderOut(decoded(fd(ddrop(decConv))))
		else:
			trainDecOut = decoderOut(decoded(fd(decConv)))
	else:
		dh1 = Dense(dim4,activation='relu',name = "DH1")
		dh2 = Dense(dim5,activation='relu',name = "DH2")
		dh3 = Dense(dim6,activation='relu',name = "DH3")
		if decMore:
			decConv = dh3(dh2(dh1((z))))
		else:
			decConv = dh2(dh1((z)))
		if decDrop:
			trainDecOut = decoderOut(decoded((ddrop(decConv))))
		else:
			trainDecOut = decoderOut(decoded((decConv)))

	vae = Model(inputs, trainDecOut)

	opt = optimizers.Adam(lr=lr) 
	
	vae.compile(loss = vae_loss(mu,log_sigma),
		optimizer=opt,metrics=['mae'])
	
	#print(vae.summary())
	
	vae.fit(train, train,
			verbose = 0,
			batch_size=batch_size,
			epochs=300,
			validation_data=(valid,valid),
			callbacks=[checkpoint,early]
			#callbacks=[checkpoint]
	)
	
	vae.load_weights(saved,by_name=True)
	
	HL_full, MAE_full = vae.evaluate(valid, valid, verbose=0)
	
	ydecoded = vae.predict(valid,  batch_size=batch_size)
	maes = np.zeros(ydecoded.shape[0], dtype='float32')
	for sampleCount in range(0,ydecoded.shape[0]):
		maes[sampleCount] = mean_absolute_error(valid[sampleCount],ydecoded[sampleCount])
	
	prc = np.percentile(maes,[95])
	sigma = np.std(maes)
	
	score = HL_full #MAE_full + sigma + prc[0]  #
	print("Score: %f Sigma: %f MAE: %f Loss: %f Perc: %f" 
		% (score,sigma,MAE_full,HL_full, prc[0]))
	return {'loss': score, 'status': STATUS_OK, 'model': vae}
	
	
def CV1D(train, valid, agedTrain, agedValid):
	
	from keras.callbacks import ModelCheckpoint
	from keras.models import Model
	from keras.layers import Dense, Input, Flatten, Reshape, Dropout
	from keras import optimizers
	from Minerva import huber_loss #,sparse_loss
	#from Minerva import 
	from keras.layers import Conv1D

	from sklearn.metrics import mean_absolute_error
	from keras.constraints import max_norm
	
	inputFeatures = 2
	outputFeatures = 2
	timesteps = 20
	dropPerc = 0.5
	
	
	hiddenActivation =  'relu'
	outputActivation = 'linear'
	
	batch_size = 64
	lr = {{choice([0.00005,0.0001,0.0002])}}
	
	
	norm = {{choice([2.,3.,4.,5.])}}
	codeSize = {{choice([7,8,9,10,11])}}
	
	
	inputs = Input(shape=(timesteps,inputFeatures),name="IN")
	c = Conv1D({{choice([16,32,48,64,96,128,256,512])}}, {{choice([2,3,4,5,6,7])}}
		,activation=hiddenActivation,name="E1")(inputs)
	
	if {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c)
			c = Conv1D({{choice([16,32,48,64,96,128,256,512])}}, {{choice([2,3,4,5,6])}}
				,kernel_constraint=max_norm(norm),activation=hiddenActivation,name="E2")(c)
		else:
			c = Conv1D({{choice([16,32,48,64,96,128,256,512])}}, {{choice([2,3,4,5,6])}}
				,activation=hiddenActivation,name="E2")(c)
		
	if {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c)
			c = Conv1D({{choice([16,32,48,64,96,128,256,512])}}, {{choice([2,3,4,5])}}
				,kernel_constraint=max_norm(norm),activation=hiddenActivation,name="E3")(c)
		else:
			c = Conv1D({{choice([16,32,48,64,96,128,256,512])}}, {{choice([2,3,4,5])}}
				,activation=hiddenActivation,name="E3")(c)
	
	preEncodeFlat = Flatten(name="F1")(c) 
	enc = Dense(codeSize,activation=hiddenActivation,name="ENC")(preEncodeFlat)
	
	c = Dense({{choice([16,32,48,64,96,128,256,512])}},activation=hiddenActivation,name="D1")(enc)
	if {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c)
			c = Dense({{choice([16,32,48,64,96,128,256,512])}}
				,kernel_constraint=max_norm(norm),activation=hiddenActivation,name="D2")(c)
		else:
			c = Dense({{choice([16,32,48,64,96,128,256,512])}}
				,activation=hiddenActivation,name="D2")(c)
	
	if {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c)
			c = Dense({{choice([16,32,48,64,96,128,256,512])}}
				,kernel_constraint=max_norm(norm),activation=hiddenActivation,name="D3")(c)
		else:
			c = Dense({{choice([16,32,48,64,96,128,256,512])}}
				,activation=hiddenActivation,name="D3")(c)
	
	c = Dense(timesteps*outputFeatures,activation=outputActivation,name="DECODED")(c)
	out = Reshape((timesteps, outputFeatures),name="OUT")(c)
	model = Model(inputs=inputs, outputs=out)
	adam = optimizers.Adam(
		lr=lr
	)	
	model.compile(loss=huber_loss, optimizer=adam,metrics=['mae'])

	#print(model.summary())
	
	path4save = "./optimizedModel.h5"
	checkpoint = ModelCheckpoint(path4save, monitor='val_loss', verbose=0,
			save_best_only=True,save_weights_only=True, mode='min')
	
	model.fit(train, train,
		verbose = 0,
		batch_size=batch_size,
		epochs=300,
		validation_data=(valid, valid)
		,callbacks=[checkpoint]
	)
	
	model.load_weights(path4save)
	
	HL_full, MAE_full = model.evaluate(valid, valid, verbose=0)
	
	ydecoded = model.predict(valid,  batch_size=batch_size)
	maes = np.zeros(ydecoded.shape[0], dtype='float32')
	for sampleCount in range(0,ydecoded.shape[0]):
		maes[sampleCount] = mean_absolute_error(valid[sampleCount],ydecoded[sampleCount])
	
	prc = np.percentile(maes,[10,90])
	sigma = np.std(maes)
	
	score =  MAE_full + prc[1]  #  #  HL_full
	print("Score: %f Sigma: %f MAE: %f Loss: %f Perc: %f" % (score,sigma,MAE_full,HL_full, prc[1]))
	return {'loss': score, 'status': STATUS_OK, 'model': model}
	
	
	
def C2D(train, valid, agedTrain, agedValid):
	
	from keras.models import load_model
	from keras.callbacks import ModelCheckpoint
	from keras.models import Model
	from keras.layers import Dense, Input, Flatten, Reshape, Dropout
	from keras import optimizers
	#from Minerva import huber_loss
	from Minerva import sparse_loss
	from keras.layers import Conv2DTranspose, Conv2D

	from keras.constraints import max_norm
	

	hiddenActivation = 'relu'
	outputActivation = 'linear'
	
	batch_size = 64
	lr = {{choice([0.00005,0.0001,0.0002])}}
	
	inputFeatures = 2
	outputFeatures = 2
	timesteps = 20
	
	dropPerc = 0.5
	strideSize = 2
	codeSize = {{choice([40,60,80])}}
	norm = {{choice([1.,2.,3.,4.,5.,6.,7.,8.])}}

	inputs = Input(shape=(timesteps,inputFeatures),name="IN")
	c = Reshape((4,5,2),name="R2E")(inputs)
	
	c = Conv2D({{choice([16,32,48,64,96,128,256,512])}},strideSize,activation=hiddenActivation,name="E1")(c)
	
	if  {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}} == 'drop':
			c = Dropout(dropPerc)(c)
			c = Conv2D({{choice([16,32,48,64,96,128,256,512])}},strideSize,
				kernel_constraint=max_norm(norm),activation=hiddenActivation,name="E2")(c)
		else:
			c = Conv2D({{choice([16,32,48,64,96,128,256,512])}},strideSize
				,activation=hiddenActivation,name="E2")(c)
	
	if  {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}} == 'drop':
			c = Dropout(dropPerc)(c)
			c = Conv2D({{choice([16,32,48,64,96,128,256,512])}},strideSize,
				kernel_constraint=max_norm(norm),activation=hiddenActivation,name="E3")(c)
		else:
			c = Conv2D({{choice([16,32,48,64,96,128,256,512])}},strideSize,
				activation=hiddenActivation,name="E3")(c)

	preEncodeFlat = Flatten(name="F1")(c) 
	enc = Dense(codeSize,activation=hiddenActivation,name="ENC")(preEncodeFlat)
	c = Reshape((1,1,codeSize),name="R2D")(enc)

	c = Conv2DTranspose({{choice([16,32,48,64,96,128,256,512])}},strideSize,
		activation=hiddenActivation,name="D1")(c)
	
	if  {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c) 
			c = Conv2DTranspose({{choice([16,32,48,64,96,128,256,512])}},strideSize,
				kernel_constraint=max_norm(norm),activation=hiddenActivation,name="D2")(c)
		else:
			c = Conv2DTranspose({{choice([16,32,48,64,96,128,256,512])}},strideSize,
				activation=hiddenActivation,name="D2")(c)
	
	if  {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c)
			c = Conv2DTranspose({{choice([16,32,48,64,96,128,256])}},strideSize,
				kernel_constraint=max_norm(norm),activation=hiddenActivation,name="D3")(c)
		else:
			c = Conv2DTranspose({{choice([16,32,48,64,96,128,256])}},strideSize,
				activation=hiddenActivation,name="D3")(c)
	
	if  {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c)
			c = Conv2DTranspose({{choice([16,32,48,64,96,128,256])}},
				strideSize,kernel_constraint=max_norm(norm),activation=hiddenActivation,name="D4")(c)
		else:
			c = Conv2DTranspose({{choice([16,32,48,64,96,128,256])}},
				strideSize,activation=hiddenActivation,name="D4")(c)
	
	preDecFlat = Flatten(name="F2")(c) 
	
	c = Dense(timesteps*outputFeatures,activation=outputActivation,name="DECODED")(preDecFlat)
	out = Reshape((timesteps, outputFeatures),name="OUT")(c)
	model = Model(inputs=inputs, outputs=out)
	adam = optimizers.Adam(
		lr=lr
	)	
	model.compile(loss=sparse_loss(enc), optimizer=adam,metrics=['mae'])
	#print(model.summary())
	path4save = "./optimizedModel.h5"
	checkpoint = ModelCheckpoint(path4save, monitor='val_loss', verbose=0,
			save_best_only=True,save_weights_only=True, mode='min')
	
	model.fit(train, train,
		verbose = 0,
		batch_size=batch_size,
		epochs=350,
		validation_data=(valid, valid)
		,callbacks=[checkpoint]
	)
	# loading the best model
	
	model.load_weights(path4save)
	
	HL_full, MAE_full = model.evaluate(valid, valid, verbose=0)

	ydecoded = model.predict(valid,  batch_size=batch_size)
	maes = np.zeros(ydecoded.shape[0], dtype='float32')
	for sampleCount in range(0,ydecoded.shape[0]):
		maes[sampleCount] = mean_absolute_error(valid[sampleCount],ydecoded[sampleCount])
	
	prc = np.percentile(maes,[90])
	sigma = np.std(maes)
	mean = np.mean(maes)
	
	score = MAE_full + prc[0] # variance + HL_full  mean + sigma + prc[0]
	print("Score: %f Sigma: %f MAE: %f Loss: %f Perc: %f MeanC: %f" % (score,sigma,MAE_full,HL_full, prc[0],mean))
	return {'loss': score, 'status': STATUS_OK, 'model': model}
	
def batchCompatible(batch_size,data):
	"""
	Transform data shape 0 in a multiple of batch_size
	"""
	exceed = data.shape[0] % batch_size
	if(exceed > 0):
		data = data[:-exceed]
	return data

def data():
	from Astrea import Astrea
	from Minerva import Minerva
	from sklearn.model_selection import train_test_split
	
	folds = 6
	minerva = Minerva(eps1=5,eps2=5,alpha1=5,alpha2=5,plotMode="GUI")	
	nameIndex = minerva.ets.dataHeader.index(minerva.ets.nameIndex)
	tsIndex = minerva.ets.dataHeader.index(minerva.ets.timeIndex)
	astrea = Astrea(tsIndex,nameIndex,minerva.ets.keepY)
	
	train_ageScale = 100
	batteries = minerva.ets.loadSyntheticBlowDataSet(train_ageScale)
	
	k_idx,k_data = astrea.kfoldByKind(batteries,folds)
	scaler = astrea.getScaler(k_data)
	folds4learn = []
	for i in range(len(k_data)):
		fold = k_data[i]
		foldAs3d = astrea.foldAs3DArray(fold,scaler)
		folds4learn.append(foldAs3d)
	trainIdx,testIdx = astrea.leaveOneFoldOut(folds)
	
	train = None
	valid = None

	#for train_index, _ in zip(trainIdx,testIdx): 
	train_index, _ = list(zip(trainIdx,testIdx))[0]
	t = [folds4learn[train_index[i]] for i in range(1,len(train_index))]
	t = np.concatenate(t)
	v = folds4learn[train_index[0]]
	train = minerva.batchCompatible(128,t)
	valid = minerva.batchCompatible(128,v)
	return train, valid, train, valid
	
	
def main():
	import time
	start = time.clock()
	best_run, best_model = optim.minimize(
										  model = FC,
										  data=data,
                                          algo=tpe.suggest,
                                          max_evals=50,
                                          trials=Trials())
	
	train, valid, agedTrain, agedValid = data()
	print("Evalutation of best performing model:")
	print(best_model.evaluate(valid, valid))
	print(best_run)
	print("Optimize - end - %f" % (time.clock() - start) )
	print(best_model.summary())
		
main()	