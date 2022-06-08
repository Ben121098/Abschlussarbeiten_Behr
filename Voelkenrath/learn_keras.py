import numpy as np
from random import randint
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Activation, Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.metrics import categorical_crossentropy
import sklearn
from sklearn.utils import shuffle
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
import itertools

### Generating the fictive data sets:
train_samples = []
train_labels = []

for i in range(50):
    random_younger = randint(13,64)
    train_samples.append(random_younger)
    train_labels.append(1)
    
    random_older = randint(65,100)
    train_samples.append(random_older)
    train_labels.append(0)
    
    
for i in range(1000):
    random_younger = randint(13,64)
    train_samples.append(random_younger)
    train_labels.append(0)    

    random_older = randint(65,100)
    train_samples.append(random_older)
    train_labels.append(1)
    

train_samples = np.array(train_samples)
train_labels = np.array(train_labels)
train_samples, train_labels = sklearn.utils.shuffle(train_samples, train_labels)    
scaler = MinMaxScaler(feature_range= (0,1))
scaled_train_samples = scaler.fit_transform(train_samples.reshape(-1,1))

### Generating the model:
model = Sequential([
    Dense(units=12, input_shape=(1,), activation="relu"),
    Dense(units=32, activation="relu"),
    Dense(units=2, activation="softmax")
])
# model.summary()


### Training and/or validating the model based on the generated data sets:
model.compile(optimizer=Adam(learning_rate=0.0001),loss="sparse_categorical_crossentropy",metrics=["accuracy"])
# model.fit(x=scaled_train_samples,y=train_labels,batch_size=10,epochs=30,shuffle=True,verbose=2)

# scaled_train_samples = scaled_train_samples[0:5]
# train_labels = train_labels[0:6]
# print(train_labels,"\n",len(train_labels),"\t",len(scaled_train_samples))

model.fit(x=scaled_train_samples,y=train_labels,batch_size=10,validation_split=0.1,epochs=30,shuffle=True,verbose=2)



### Predicting based on a given data set using the trained model:
predictions = model.predict(x=scaled_train_samples,batch_size=10, verbose=1)
rounded_predictions = np.argmax(predictions,axis=-1)
confusion_matrix()
# for i in predictions:
#     print(i,"\t",i[0]+i[1])






