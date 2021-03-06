#Standard
import uuid,time,os,logging, numpy as np, matplotlib.pyplot as plt
from logging import handlers as loghds
#Project module
from Demetra import EpisodedTimeSeries
#Kers
from keras.models import Sequential, Model
from keras.layers import Dense, Input, concatenate, Flatten, Reshape, LSTM, Lambda
from keras.layers import Conv1D
from keras.layers import Conv2DTranspose, Conv2D, Dropout
from keras.models import load_model
from keras import optimizers
from keras.callbacks import EarlyStopping, CSVLogger, ModelCheckpoint, ReduceLROnPlateau
import tensorflow as tf
#Sklearn
from sklearn.metrics import mean_absolute_error, mean_squared_error
from keras.constraints import max_norm

from keras.losses import mse, binary_crossentropy

import keras.backend as K
from sklearn.manifold import TSNE

#KERAS ENV GPU
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['NUMBAPRO_NVVM']=r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v8.0\nvvm\bin\nvvm64_31_0.dll'
os.environ['NUMBAPRO_LIBDEVICE']=r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v8.0\nvvm\libdevice'

#Module logging
logger = logging.getLogger("Minerva")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s][%(name)s][%(levelname)s] %(message)s')
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler) 

isVae = False
codeDimension = 13 #11 # # 80

'''
 ' Huber loss.
 ' https://jaromiru.com/2017/05/27/on-using-huber-loss-in-deep-q-learning/
 ' https://en.wikipedia.org/wiki/Huber_loss
'''
def huber_loss(y_true, y_pred, clip_delta=1.0):
	error = y_true - y_pred	
	cond  = tf.keras.backend.abs(error) < clip_delta
	squared_loss = 0.5 * tf.keras.backend.square(error)
	linear_loss  = clip_delta * (tf.keras.backend.abs(error) - 0.5 * clip_delta)
	return tf.where(cond, squared_loss, linear_loss)

def sparse_loss(code):
	def loss(y_true, y_pred):
		sparseLoss = K.mean(K.abs(code))
		reconstruction_loss = K.mean((huber_loss(y_true,y_pred)))
		finalLoss = reconstruction_loss + sparseLoss
		return finalLoss
	return loss
	
def vae_loss(mu,sigma):
	def loss(y_true, y_pred):
		#kl_loss = 0.5 * K.mean(K.exp(z_log_var) + K.square(z_mean) - 1. - z_log_var, axis=1)
		kl_loss = -0.5 * K.sum(1 + K.log(K.square(sigma)) - K.square(mu) - K.square(sigma))
		reconstruction_loss = huber_loss(y_true,y_pred) #K.mean()
		vaeLoss = reconstruction_loss + kl_loss
		return vaeLoss
	return loss
	
def sample_z(args):
	mu, log_sigma = args
	eps = K.random_normal(shape=(codeDimension,),mean=0.,stddev=1.)
	return mu + K.exp(log_sigma / 2) * eps

class Minerva():
		
	logFolder = "./logs"
	modelName = "FullyConnected_4_"
	modelExt = ".h5"
	batchSize = 64
	lr = 0.0002
	minlr = 0.00001
	epochs = 1000
	ets = None
	eps1   = 5
	eps2   = 5
	alpha1 = 5
	alpha2 = 5
	
	def getModel(self,inputFeatures,outputFeatures,timesteps):
		#return self.conv1DQR(inputFeatures,outputFeatures,timesteps)
		return self.Conv2DQR(inputFeatures,outputFeatures,timesteps)
		#return self.FullyConnected(inputFeatures,outputFeatures,timesteps)
		
	def codeProjection(self,name4model,x_valid):
		
		path4save = os.path.join( self.ets.rootResultFolder , name4model+self.modelExt )
		
		_,encoder,_ = self.loadModel(path4save,2,2,20)
		
		valid_decoded = None
		samples = []
		codes = []
		tsne = TSNE(n_components=2, n_iter=1000)
		if(encoder is not None):
			if(isVae == True):
				m,s = encoder.predict(x_valid)
				np.random.seed(42)
				for i in range(0,m.shape[0]):
					eps = np.random.normal(0, 1, codeDimension)
					z = m[i] + np.exp(s[i] / 2) * eps
					samples.append(z)
				samples = np.asarray(samples)
			else:
				samples = encoder.predict(x_valid)
			
			proj = tsne.fit_transform(samples)
			codes.append(proj)
			for code in codes:
				plt.scatter(code[:,0],code[:,1])
				
		
		
		
	def __init__(self,eps1,eps2,alpha1,alpha2,plotMode = "server"):
	
		# plotMode "GUI" #"server" # set mode to server in order to save plot to disk instead of showing on video
		# creates log folder
		if not os.path.exists(self.logFolder):
			os.makedirs(self.logFolder)
		
		self.eps1   = eps1
		self.eps2   = eps2
		self.alpha1 = alpha1
		self.alpha2 = alpha2
		
		logFile = self.logFolder + "/Minerva.log"
		hdlr = loghds.TimedRotatingFileHandler(logFile,
                                       when="H",
                                       interval=1,
                                       backupCount=30)
		hdlr.setFormatter(formatter)
		logger.addHandler(hdlr)
		self.ets = EpisodedTimeSeries(self.eps1,self.eps2,self.alpha1,self.alpha2)
		
		if(plotMode == "server" ):
			plt.switch_backend('agg')
			if not os.path.exists(self.ets.episodeImageFolder):
				os.makedirs(self.ets.episodeImageFolder)

				
	def loadModel(self,path4save,inputFeatures,outputFeatures,timesteps):
		vae, encoder, decoder = self.getModel(inputFeatures,outputFeatures,timesteps)
		vae.load_weights(path4save,by_name=True)
		if(encoder is not None):
			encoder.load_weights(path4save,by_name=True)
		if(decoder is not None):
			decoder.load_weights(path4save,by_name=True)
		return vae, encoder, decoder
	
	
	def FullyConnected(self,inputFeatures,outputFeatures,timesteps):
		
		codeSize = codeDimension
		
		ha = 'relu'
		oa = 'linear'
		
		inputs = Input(shape=(timesteps,inputFeatures),name="IN")
		e1 = Dense(256,activation=ha,name="EFC1")
		e2 = Dense(128,activation=ha,name="EFC2")
		e3 = Dense(512,activation=ha,name="EFC3")
		preEncodeFlat = Flatten(name="EF1")
		enc = Dense(codeSize,activation=ha,name="CODE")
		
		encoderOut = enc(preEncodeFlat(e3(e2(e1(inputs)))))
		encoder = Model(inputs,encoderOut)
		
		d1 = Dense(256,activation=ha,name="D1")
		d2 = Dense(96,activation=ha,name="D2")
		decoded = Dense(timesteps*outputFeatures,activation=oa,name="REC")
		out = Reshape((timesteps, outputFeatures),name="OUT")
		
		latent_inputs = Input(shape=(codeSize,), name='CODE_IN')
		decoderOut = out( decoded(d2(d1((latent_inputs))))) 
		
		decoder = Model(latent_inputs,decoderOut)
		
		trainDecOut = out( decoded(d2(d1((encoderOut))))) 
		autoencoderModel = Model(inputs=inputs, outputs=trainDecOut)
		opt = optimizers.Adam(lr=self.lr) 
		autoencoderModel.compile(loss=huber_loss, optimizer=opt,metrics=['mae'])
		return autoencoderModel,  encoder, decoder
		
		
	def Conv2DQR(self,inputFeatures,outputFeatures,timesteps):
		
		strideSize = 2
		codeSize = codeDimension
		outputActivation = 'linear'
		hiddenActication = 'relu'
	
		inputs = Input(shape=(timesteps,inputFeatures),name="IN")
		e1 = Reshape((4,5,2),name="R2E")
		e2 = Conv2D(128,strideSize,activation=hiddenActication,name="E1")
		e3 = Conv2D(512,strideSize,activation=hiddenActication,name="E2")
		e4 = Flatten(name="EF1") 
		code = Dense(codeSize,activation=hiddenActication,name="CODE")
		
		d1 = Reshape((1,1,codeSize),name="R2D")
		d2 = Conv2DTranspose(512,strideSize,activation=hiddenActication,name="D1")
		d3 = Flatten(name="DF1")
		d4 = Dense(timesteps*outputFeatures,activation=outputActivation,name="DECODED")
		out = Reshape((timesteps, outputFeatures),name="OUT")
		encoderOut = code(e4(e3(e2(e1(inputs)))))
		encoder = Model(inputs=inputs, outputs=encoderOut)
		latent_inputs = Input(shape=(codeSize,), name='CODE_IN')
		decoderOut = out(d4(d3(d2(d1((latent_inputs)))))) 
		trainDecoderOut = out(d4(d3(d2(d1(encoderOut)))))
		decoder = Model(latent_inputs,decoderOut)
		autoencoderModel = Model(inputs=inputs, outputs=trainDecoderOut)
		opt = optimizers.Adam(lr=self.lr) 
		autoencoderModel.compile(loss=huber_loss, optimizer=opt,metrics=['mae'])
		return autoencoderModel, encoder, decoder
	
	def conv1DQR(self,inputFeatures,outputFeatures,timesteps):
		
		codeSize = codeDimension
		
		ha = 'relu'
		oa = 'linear'
		
		inputs = Input(shape=(timesteps,inputFeatures),name="IN")
		e1 = Conv1D(32,2,activation=ha,name="EC1")
		e2 = Conv1D(256,6,activation=ha,name="EC2")
		e3 = Dropout(.5,name="ED1")
		e4 = Conv1D(256,5,activation=ha,kernel_constraint=max_norm(5.),name="EC3")
		preEncodeFlat = Flatten(name="EF1")
		enc = Dense(codeSize,activation=ha,name="CODE")
		
		encoderOut = enc(preEncodeFlat(e4(e3(e2(e1(inputs))))))
		encoder = Model(inputs,encoderOut)
		
		d1 = Dense(32,activation=ha,name="D1")
		d2 = Dense(512,activation=ha,name="D2")
		decoded = Dense(timesteps*outputFeatures,activation=oa,name="REC")
		out = Reshape((timesteps, outputFeatures),name="OUT")
		
		latent_inputs = Input(shape=(codeSize,), name='CODE_IN')
		decoderOut = out( decoded(d2(d1((latent_inputs))))) 
		
		decoder = Model(latent_inputs,decoderOut)
		
		trainDecOut = out( decoded(d2(d1((encoderOut))))) 
		autoencoderModel = Model(inputs=inputs, outputs=trainDecOut)
		opt = optimizers.Adam(lr=self.lr) 
		autoencoderModel.compile(loss=huber_loss, optimizer=opt,metrics=['mae'])
		return autoencoderModel,  encoder, decoder

	def getMaes(self,testX,ydecoded):
		maes = np.zeros(ydecoded.shape[0], dtype='float32')
		for sampleCount in range(0,ydecoded.shape[0]):
			maes[sampleCount] = mean_absolute_error(testX[sampleCount],ydecoded[sampleCount])
		return maes

	def trainlModelOnArray(self,x_train, y_train, x_valid, y_valid,name4model):
		
		tt = time.clock()
		logger.debug("trainlModelOnArray - start")
		
		x_train = self.__batchCompatible(self.batchSize,x_train)
		y_train = self.__batchCompatible(self.batchSize,y_train)
		x_valid = self.__batchCompatible(self.batchSize,x_valid)
		y_valid = self.__batchCompatible(self.batchSize,y_valid)
		
		logger.debug("Training model %s with train %s and valid %s" % (name4model,x_train.shape,x_valid.shape))

		inputFeatures  = x_train.shape[2]
		outputFeatures = y_train.shape[2]
		timesteps =  x_train.shape[1]
		
		model,_,_ = self.getModel(inputFeatures,outputFeatures,timesteps)
	
		path4save = os.path.join( self.ets.rootResultFolder , name4model+self.modelExt )
		checkpoint = ModelCheckpoint(path4save, monitor='val_loss', verbose=0,
			save_best_only=True, mode='min',save_weights_only=True)
		
		rop = ReduceLROnPlateau(monitor='val_loss', factor=0.5,
									patience=50, min_lr=self.minlr,cooldown=10,verbose=0, mode='min')
		
		early = EarlyStopping(monitor='val_loss',
			min_delta=0.000001, patience=100, verbose=1, mode='min')
				
		history  = model.fit(x_train, x_train,
			verbose = 0,
			batch_size=self.batchSize,
			epochs=self.epochs,
			validation_data=(x_valid,x_valid)
			,callbacks=[checkpoint,early,rop]
		)
		elapsed = (time.clock() - tt)
		
		historySaveFile = name4model+"_history"
		self.ets.saveZip(self.ets.rootResultFolder,historySaveFile,history.history)
		logger.info("Training completed. Elapsed %f second(s)." %  (elapsed))
		
		model,encoder,decoder = self.loadModel(path4save,2,2,20)
		
		valid_decoded = None
		#if(encoder is not None):
		if(isVae == True):
			m,s = encoder.predict(x_valid)
			np.random.seed(42)
			samples = []
			for i in range(0,m.shape[0]):
				eps = np.random.normal(0, 1, codeDimension)
				z = m[i] + np.exp(s[i] / 2) * eps
				samples.append(z)
			
			samples = np.asarray(samples)
			valid_decoded = decoder.predict(samples)
		else:
			valid_decoded = model.predict(x_valid)
			
		valMae = self.getMaes(x_valid,valid_decoded)
		logger.info("Training completed. Valid MAE %f " %  (valMae.mean()) )
		
	def evaluateModelOnArray(self,testX,testY,model2load,plotMode,scaler=None,showImages=True,num2show=5,phase="Test",showScatter = False):
		
		path4save = os.path.join( self.ets.rootResultFolder ,model2load+self.modelExt)
		testX = self.__batchCompatible(self.batchSize,testX)
		model , encoder, decoder = self.loadModel(path4save,2,2,20)
		ydecoded = None

		if(isVae == True):
			m,s = encoder.predict(testX)
			np.random.seed(42)
			samples = []
			for i in range(0,m.shape[0]):
				eps = np.random.normal(0, 1, codeDimension)
				z = m[i] + np.exp(s[i] / 2) * eps
				samples.append(z)

			samples = np.asarray(samples)
			ydecoded = decoder.predict(samples)
		else:
			ydecoded = model.predict(testX)
		
		maes = self.getMaes(testX,ydecoded)
		logger.info("Test MAE %f " %  (maes.mean()))
		return maes
	
	def	batchCompatible(self,batch_size,data):
		return self.__batchCompatible(batch_size,data)
		
	def __batchCompatible(self,batch_size,data):
		"""
		Transform data shape 0 in a multiple of batch_size
		"""
		exceed = data.shape[0] % batch_size
		if(exceed > 0):
			data = data[:-exceed]
		return data