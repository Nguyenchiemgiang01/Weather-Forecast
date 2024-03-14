import RPi.GPIO as GPIO
import Adafruit_DHT
from time import sleep
import threading
import pandas as pd
import requests
import sys
import json
from datetime import datetime
from tensorflow import keras
import numpy as np
import BlynkLib
import RPi.GPIO as GPIO
#from BlynkTimer import BlynkTimer



#BLYNK_AUTH_TOKEN "ImaXaqiRzflbDkvb-VUKI7q3piZjMcJJ"
#blynk = BlynkLib.Blynk(BLYNK_AUTH_TOKEN)
#timer = BlynkTimer()
motor_IN1=6
motor_IN2=13
switch1=17
switch2=27
button=2
rainsensor = 22
DHTpin = 10
sensor_light = 23
led = 21
sensor = Adafruit_DHT.DHT11

rack_status=0 #O is close and 1 is open
motor_status=0 #0 is stop and 1 is run


def setup():
    GPIO.setwarnings(False)
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(motor_IN1,GPIO.OUT)
    GPIO.setup(motor_IN2,GPIO.OUT)
    GPIO.setup(rainsensor,GPIO.IN)
    GPIO.setup(switch1,GPIO.IN)
    GPIO.setup(switch2,GPIO.IN)
    GPIO.setup(button,GPIO.IN)
    GPIO.setup(sensor_light,GPIO.IN)
    GPIO.setup(led,GPIO.OUT)
    for i in range(3):
        GPIO.output(led, GPIO.HIGH)
        sleep(0.25)
        GPIO.output(led, GPIO.LOW)
        sleep(0.25)

def motor_up():
    '''close the rack'''
    global motor_status
    motor_status=1
    GPIO.output(motor_IN1,GPIO.HIGH)
    GPIO.output(motor_IN2,GPIO.LOW)
    print('motor up')
    
def motor_down():
    '''open the rack'''
    global motor_status
    motor_status=1
    GPIO.output(motor_IN1,GPIO.LOW)
    GPIO.output(motor_IN2,GPIO.HIGH)
    print('motor down')
    
def motor_stop():
    '''stop motor rack'''
    global motor_status
    motor_status=0
    GPIO.output(motor_IN1,GPIO.LOW)
    GPIO.output(motor_IN2,GPIO.LOW)
    print('motor stop')
    
def switch_up(channel=0):
    global rack_status
    motor_stop() # Rack is opening
    rack_status=1 # Rack status is open
    print('rack switch up')
    GPIO.output(led, GPIO.HIGH)
    motor_down()
    sleep(0.05)
    motor_stop()
    
def switch_down(channel=0):
    global rack_status
    motor_stop()
    rack_status=0 #rack is closed
    print('rack switch down')
    GPIO.output(led, GPIO.LOW)
    motor_up()
    sleep(0.05)
    motor_stop()
    
def button_press(channel=0):
    if rack_status == 0 and motor_status == 0:
        motor_up()
    elif  rack_status == 1 and motor_status == 0:
        motor_down()
    else:
        motor_stop()
def reainseroron(channel=0):
    if rack_status == 1: # Rack is open 
        motor_down()

def print_tem_hur():
    while True:
        now = datetime.now()
        dk = now.strftime('%M')
        if int(dk) < 10:
            humidity, temperature = Adafruit_DHT.read_retry(sensor, DHTpin)
            print(f'Nhiet do: {temperature}; Do am: {humidity}')
            data = pd.read_csv('temp_humidity.csv')
            data.loc[len(data)+1] = [temperature - 3, humidity]
            data = data.tail(12)
            data.to_csv('temp_humidity.csv', index = False)
            
        sleep(300)

def lightsensor(channel=0):
    if rack_status == 1: # Rack is open 
        motor_down()
def result(pre_value, con_value):
    raquyetdinh=False
    lab_con=['Overcast','Rain, Partially cloudy','Rain, Overcast']
    i=0
    for _ in pre_value:
        i+=1 
        if _>50 :
            raquyetdinh=True
            break
    j=0
    for lab in con_value:
        j+=1
        if lab in lab_con:
            raquyetdinh=True
            break
    time_re = 0
    if raquyetdinh==True:
        if i<j:
            time_re=i
        else:
            time_re=j
    time_re -=1
    return raquyetdinh, time_re

def run_model():
    print('model is started')
    #Đọc dataset
    data = pd.read_csv('data_predict.csv')

    
    model_predict_codition = keras.models.load_model('model_predict_condition.h5')
    model_predict_precip = keras.models.load_model('model_predict_precip.h5')
    model_predict_temp= keras.models.load_model('model_predict_temp.h5')
    
    while True:
        #Lấy ngày giờ hiện tại
        now = datetime.now()
        ngay = now.strftime('%Y-%m-%d')
        gio = now.strftime('%H')
        
        response = requests.request("GET", f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/Da%20Nang/{ngay}/{ngay}?unitGroup=metric&include=hours&key=VD7W3KWW2N5KLCQCS5DZPAMHQ&contentType=json")
        if response.status_code!=200:
          print('Unexpected Status code: ', response.status_code)
          sys.exit()
          
        # Parse the results as JSON
        jsonData = response.json()
          
        #Nối vào dataset
        for i in range(12):
          days = jsonData['days'][0]['hours'][int(gio)-i]
          new_data = [days['temp'], days['dew'], days['humidity'], days['precip'], days['precipprob'], days['windspeed'], days['winddir'], days['cloudcover'], days['visibility'], days['solarradiation'],days['solarenergy'], days['uvindex'], days['conditions']]
          data.loc[len(data)+i] = new_data
          
        temp_humidity = pd.read_csv('temp_humidity.csv')


        X = pd.DataFrame(data[['temp','dew','humidity','precip','windspeed','winddir','cloudcover','visibility','solarradiation','solarenergy','conditions','precipprob']])
        X['temp'] = temp_humidity['temp']
        X['humidity'] = temp_humidity['humidity']
        print(X)
        
        X['conditions'] = X['conditions'].replace('Clear', 0)
        X['conditions'] = X['conditions'].replace('Partially cloudy', 1)
        X['conditions'] = X['conditions'].replace('Overcast', 2)
        X['conditions'] = X['conditions'].replace('Rain, Partially cloudy', 3)
        X['conditions'] = X['conditions'].replace('Rain, Overcast', 4)
        X.loc[X['precipprob']==100,'precipprob']=1
        
        X_test = X[-12:]
        X_test = X_test.to_numpy().reshape(1,12,12)
        
        y_precip_predict = model_predict_precip.predict(X_test).flatten()
        y_condition_predict = model_predict_codition.predict(X_test).flatten()
        y_temp_predict = model_predict_temp.predict(X_test).flatten()
        print(y_precip_predict)
        y_precip_predict[y_precip_predict < 0] +=0.05
        y_precip_predict=rounded_arr = np.round(y_precip_predict * 100, decimals=1)
        y_temp_predict=rounded_arr = np.round(y_temp_predict+2, decimals=0)

        y_precip_predict = y_precip_predict.flatten()
        y_condition_predict = y_condition_predict.flatten()
        y_temp_predict=y_temp_predict.flatten()


        y_condition_predict = pd.Series(y_condition_predict.round().astype(int))
        y_condition_predict = y_condition_predict.replace(0, 'Clear')
        y_condition_predict = y_condition_predict.replace(1, 'Partially cloudy')
        y_condition_predict = y_condition_predict.replace(2, 'Overcast')
        y_condition_predict = y_condition_predict.replace(3, 'Rain, Partially cloudy')
        y_condition_predict = y_condition_predict.replace(4, 'Rain, Overcast')


        data = {
            'precipprob': y_precip_predict,
            'condition': list(y_condition_predict),
            'temp': y_temp_predict
        }

        df = pd.DataFrame(data)
        
        pre_value=[]
        con_value=[]

        for index, row in df.iterrows():
            pre_value .append( row['precipprob'])
            con_value .append(row['condition'])
        
        rs, time = result(pre_value, con_value)
        print('ket qua:',rs,'time close', time)
        timesleep = 10800
        if rs:
            time_close_rask = time*3600
            timesleep -= time_close_rask
            sleep(time_close_rask)
            if rack_status == 1: # Rack is open 
                motor_down()
        
        sleep(timesleep)

if __name__ == '__main__':
    setup()
    print('setup...Start!')
    motor_stop()
    GPIO.add_event_detect(switch1,GPIO.FALLING,callback=switch_up,bouncetime=300)
    GPIO.add_event_detect(switch2,GPIO.FALLING,callback=switch_down,bouncetime=300)
    GPIO.add_event_detect(button,GPIO.FALLING,callback=button_press,bouncetime=300)
    GPIO.add_event_detect(rainsensor,GPIO.FALLING,callback=reainseroron,bouncetime=300)
    GPIO.add_event_detect(sensor_light, GPIO.RISING, callback=lightsensor, bouncetime=300)
    threadtemp = threading.Thread(target=print_tem_hur)
    threadtemp.start()
    threadmodel= threading.Thread(target=run_model)
    threadmodel.start()
    
    while True:
        pass

    
    GPIO.cleanup()