#Standard Imports
import time,os,logging, matplotlib.pyplot as plt, numpy as np
from math import sqrt,ceil,trunc
import pandas as pd

#Project module import
from Demetra import EpisodedTimeSeries

from keras.models import Sequential, Model
from keras.layers import LSTM, Dense, TimeDistributed, Bidirectional, RepeatVector, Input, Dropout, Activation
from keras.layers import Conv2D, MaxPooling2D, Flatten, UpSampling2D, Conv1D, UpSampling1D, MaxPooling1D
from keras.models import load_model
from keras import optimizers
from numpy import array

#KERAS ENV GPU
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['NUMBAPRO_NVVM']=r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v8.0\nvvm\bin\nvvm64_31_0.dll'
os.environ['NUMBAPRO_LIBDEVICE']=r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v8.0\nvvm\libdevice'

#Module logging
logger = logging.getLogger("Minerva")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(name)s][%(levelname)s] %(message)s')
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)

def main():
	ets = EpisodedTimeSeries(30)

	ets.buildEpisodedDataset(os.path.join(".","dataset"))
	ets.buildScaledDataset()
	
	minerva = Minerva()
	#if(True):
	if(False):
		x_train, y_train, x_valid, y_valid,scaler = ets.loadTrainset()	
		#minerva.trainModel(x_train, y_train, x_valid, y_valid)
		minerva.trainSequentialModel(x_train, y_train, x_valid, y_valid)
	else:
		x_test, y_test, scaler = ets.loadTestset()	
		minerva.evaluateModel(x_test, y_test)
		
	#DEBUG PURPOSE ONLY
	#x_test, y_test, scaler = ets.loadTestset()	
	#ets.showEpisodes(scaler)
		
		
class Minerva():

	#modelName = "modelloNuovo.h5"
	#modelName = "bidirectional_episoded_deepModel.h5"
	modelName = "Convolutional_DeepModel.h5"
	batchSize = 250
	epochs = 30
	
	def trainSequentialModel(self,x_train, y_train, x_valid, y_valid):
		
		x_train = self.batchCompatible(self.batchSize,x_train)
		y_train = self.batchCompatible(self.batchSize,y_train)
		x_valid = self.batchCompatible(self.batchSize,x_valid)
		y_valid = self.batchCompatible(self.batchSize,y_valid)
		
		
		
		x_train = x_train[:,:-1,:].copy() 
		y_train = y_train[:,:-1,:].copy() 
		x_valid = x_valid[:,:-1,:].copy() 
		y_valid = y_valid[:,:-1,:].copy() 
		
		
		logger.info(x_train.shape)
		logger.info(y_train.shape)
		logger.info(x_valid.shape)
		logger.info(y_valid.shape)
		
		
		tt = time.clock()
		
		inputFeatures  = x_train.shape[2]
		outputFeatures = y_train.shape[2]
		
		hiddenStateDim0 = 1024
		hiddenStateDim1 = 512
		hiddenStateDim2 = 128
		
		timeSteps =  x_train.shape[1]
		
		model = Sequential()
		
		model.add(Conv1D(hiddenStateDim0, kernel_size=4, strides=4,
                 activation='tanh',input_shape=(timeSteps,inputFeatures)))
				 
		model.add(MaxPooling1D(pool_size=4, strides=None, padding='same'))
		
		#model.add(Conv1D(hiddenStateDim1, kernel_size=2, strides=2,
        #         activation='relu'))
		#model.add(MaxPooling1D(pool_size=2, strides=None, padding='same'))		 
		
		#model.add(Conv1D(hiddenStateDim1, kernel_size=2, strides=2,
        #         activation='tanh'))
		#model.add(UpSampling1D(2))
		#
		#model.add(Conv1D(hiddenStateDim0, kernel_size=2, strides=2,
        #         activation='relu'))
		model.add(UpSampling1D(3)) # 6
		model.add(Conv1D(hiddenStateDim1, kernel_size=1, strides=1,
                 activation='relu'))
		model.add(UpSampling1D(5)) # 30
		model.add(Conv1D(hiddenStateDim1, kernel_size=1, strides=1,
                 activation='tanh'))
		
		model.add(TimeDistributed(Dense(hiddenStateDim2, activation='relu')))
		model.add(TimeDistributed(Dense(outputFeatures, activation='tanh')))
		
		adam = optimizers.Adam(lr=0.00001)		
		model.compile(loss='mean_squared_error', optimizer=adam,metrics=['mae'])
		print(model.summary())
		
		dummy_train = np.zeros([x_train.shape[0],x_train.shape[1],1],dtype='int16')
		dummy_valid = np.zeros([x_valid.shape[0],x_valid.shape[1],1],dtype='int16')
		model.fit(x_train, y_train,
			batch_size=self.batchSize,
			epochs=self.epochs,
			validation_data=(x_valid,y_valid)
		)
	
		model.save(self.modelName)  # creates a HDF5 file 'batteryLSTM.h5'
		logger.info("Training completed. Elapsed %f second(s)" %  (time.clock() - tt))
		return model
				
		
	def evaluateModel(self,x_test,y_test):
		model = load_model(self.modelName)
		x_test = self.batchCompatible(self.batchSize,x_test)
		y_test = self.batchCompatible(self.batchSize,y_test)
		
		x_test = x_test[:,:-1,:].copy() 
		y_test = y_test[:,:-1,:].copy() 
		
		
		
		mse, mae = model.evaluate( x=x_test, y=y_test, batch_size=self.batchSize, verbose=0)
		logger.info("MSE %f - MAE %f" % (mse,mae))
	
		y_pred = model.predict(x_test,  batch_size=self.batchSize)
		
		
		for r in range(25):
			plt.figure()
			toPlot = r #np.random.randint(y_pred.shape[0])
			i = 1
			for col in range(y_pred.shape[2]):
				plt.subplot(y_pred.shape[2], 1, i)
				plt.plot(y_pred[toPlot][:, col],color="navy")
				plt.plot(y_test[toPlot][:, col],color="orange")
				i += 1
			plt.show()
	
	
		
		
	def batchCompatible(self,batch_size,data):
		exceed = data.shape[0] % batch_size
		if(exceed > 0):
			data = data[:-exceed]
		return data
	
		
main()

