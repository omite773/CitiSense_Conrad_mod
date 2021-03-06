from bluetooth import *
import subprocess
import os
import signal
import requests
import csv
from datetime import datetime

from time import sleep

def saveFile():
    subprocess.call("sudo cp /home/pi/weather/weatherlog.csv /home/pi/weather/weatherlog"+datetime.now().strftime('%Y-%m-%d_%H:%M')+".csv",shell=True)

def FormatData():
    result =list(csv.reader(open("/home/pi/weather/weatherlog.csv")))

    for s in result[1:]:
        date = s[0]
        time = s[1]
        hum_inside = s[2]
        temp_inside = s[3]
        hum_outside = s[4]
        temp_outside = s[5]
        abs_pressure = s[6]
        wind_ave = s[7]
        wind_gust= s[8]
        wind_dir= s[9]
        rain = s[10]
        sdata = {"sensid": "Citisense", "Date" : date, "Time": time, "Hum_in_RH": hum_inside, "Temp_in_C": temp_inside, "Hum_out_RH": hum_outside,"Temp_out_C": temp_outside, "Abs_pressure_hpa": abs_pressure, "Wind_ave_kmh": wind_ave, "Wind_gust_kmh": wind_gust, "Wind_dir": wind_dir, "Rain_mm": rain}
        try:
            r = requests.post("https://citizensensing.itn.liu.se/cs/setsdata", json = sdata)
            print(r.status_code, r.reason)
        except:
            client_socket.send("Failed to connect to server!")

def send_file(s,dir):

    size = os.path.getsize(dir)
    file = open(dir,'rb')
    #Send filename
    s.send(dir)
    s.send('\n')
    packet = 1
    #Send file in 1KB-parts, maximum for bluetooth.send()
    while(packet):
        packet = file.read(1024)
        try:
            s.send(packet)
        except BluetoothError:
            #Exit if client disconnect
            packet = None
            print("Disconnected")
    file.close()

def is_connected(s):
    try:
        #If client connected, this does not throw error
        s.getpeername()
        return True
    except:
        return False

#Create blutoothsocket with RFCOMM protocol
pisocket = BluetoothSocket( RFCOMM )
#Bind socket to any port
pisocket.bind(("", PORT_ANY))
#Listen for 1 client
pisocket.listen(10)

#Instantiate webapp
webapp = None
#webapp = subprocess.Popen("sudo python3 /home/pi/citisense/webappl.py", shell=True, stdout=subprocess.PIPE, preexec_fn=os.setsid)
#Start with wifi-ap off
wifipower = False
#subprocess.call("sudo service hostapd stop",shell=True)
#sleep(1)
#subprocess.call("sudo ifconfig wlan0 down",shell=True)

def recieve(sock,cnt):
    data = 10 # ASCII \n
    ret = bytearray()
    try:
        #Wait for command as long as client is connected
        while(is_connected(client_socket) and cnt>0):
            data = client_socket.recv(1)
            if data[0] != 10:
                ret.extend(data)
                cnt = cnt - 1
    except BluetoothError:
        print("Client disconnected")
        return None
    return ret.decode("ASCII")

while(1):
    #Accept connection, get client socket
    client_socket,adr = pisocket.accept()
    while(is_connected(client_socket)):
        description = recieve(client_socket,1)
        print(str(description))
        if description == 'S': #ASCII S
            # 'S' means send data logs
            
            send_file(client_socket, "/home/pi/weather/weatherlog.csv")
            print("Done")

        elif description == 'P':
            # 'P' means send picture
            
            #send_file(client_socket, "/home/pi/citisense/logs/pic.jpg")
            subprocess.call("sudo reboot",shell=True)
            print("Done")
                
        elif description == 'D' : #Ascii D
            year = recieve(client_socket,2)
            month = recieve(client_socket,2)
            day = recieve(client_socket,2)
            hour = recieve(client_socket,2)
            minute = recieve(client_socket,2)
            subprocess.call('sudo date +%Y%m%d -s "20'+str(year)+str(month)+str(day)+'"',shell=True)
            subprocess.call('sudo date +%T -s "'+str(hour)+':'+str(minute)+':00"',shell=True)

        elif description == 'L': #ASCII w
            # w means turn off wifi and webserver
            #os.killpg(os.getpgid(webapp.pid), signal.SIGTERM)
            #subprocess.call("sudo service hostapd stop",shell=True)
            #sleep(1)
            subprocess.call("sudo ifconfig wlan0 down",shell=True)
            #wifipower = False
            
        elif description == 'W': #ASCII W
            # W means start wifi and webserver
            subprocess.call("sudo ifconfig wlan0 up",shell=True)
            subprocess.call("sudo service hostapd start",shell=True)
            sleep(4)
            subprocess.call("sudo service hostapd restart",shell=True)
            sleep(2)
            subprocess.call("sudo service hostapd restart",shell=True)
            webapp = subprocess.Popen("sudo python3 /home/pi/citisense/webappl.py", shell=True, stdout=subprocess.PIPE, preexec_fn=os.setsid)
            wifipower = True
            sleep(1)
            subprocess.call("sudo service xrdp restart",shell=True)
            
        elif description == 'Z': #ASCII W
            # W means start wifi and webserver
            saveFile()
            subprocess.call("sudo rfkill unblock wifi",shell=True)
            subprocess.call("sudo ifconfig wlan0 up",shell=True)
            client_socket.send("Sleep...\n")
            sleep(15) 
            FormatData()
            client_socket.send("Data uploaded to server\n")
            send_file(client_socket, "/home/pi/weather/weatherlog.csv")
            wifipower = True
            subprocess.call("sudo ifconfig wlan0 down", shell=True)
            wifipower = False
            filename = "/home/pi/weather/weatherlog.csv"
            sleep(1)
            f = open(filename, "w+")
            sleep(1)
            file.write('Date, Time[UTC], Hum_inside[RH], Temp_inside[C], Hum_outside[RH], Temp_outside[C], Abs_pressure[hpa], wind_ave[m/s], wind_gust[m/s], wind_dir, rain[mm]\n')
            sleep(1)
            client_socket.send("File cleared!\n")
            f.close
            client_socket.send("Done\n")

        elif description == 'O': #Turn the HUB on
            subprocess.call("echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/bind",shell=True)
            print("HUB = on")
            client_socket.send("HUB = on\n")
            
        elif description == 'F': #Turn the HUB off
            subprocess.call("echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/unbind",shell=True)
            print("HUB = off")
            client_socket.send("HUB = off\n")
        elif description == 'C':  #Clear the log file
            filename = "/home/pi/citisense/logs/data_log.csv"
            sleep(1)
            f = open(filename, "w+")
            sleep(1)
            f.write('Date, Time, Hum_inside, Temp_inside[C], Hum_outside, Temp_outside[C], Abs_pressure[hpa], wind_ave[m/s], wind_gust[m/s], wind_dir, rain[mm]\n')
            sleep(1)
            client_socket.send("File cleared!\n")
            f.close
        elif description == 'A': #Access point
            subprocess.call("sudo cp /home/pi/citisense/dhcpcd_ap.conf /etc/dhcpcd.conf",shell=True)
            sleep(1)
            subprocess.call("sudo cp /home/pi/citisense/interfaces_ap /etc/network/interfaces",shell=True)
            client_socket.send("Rebooting!\n")
            subprocess.call("reboot",shell=True)
        elif description == 'T': #Wifi
            subprocess.call("sudo cp /home/pi/citisense/dhcpcd_wifi.conf /etc/dhcpcd.conf",shell=True)
            sleep(1)
            subprocess.call("sudo cp /home/pi/citisense/interfaces_wifi /etc/network/interfaces",shell=True)
            client_socket.send("Rebooting!\n")
            subprocess.call("reboot",shell=True)
        elif description == 'R': #Remote desktop
            subprocess.call("sudo service xrdp start",shell=True)
            client_socket.send("xrdp started!!\n")
            client_socket.send("Username: Pi\n Password: citiproj321\n")
        elif description == 'H': #Help with commands
            client_socket.send("A - Acess point\n C - Clear log file\n D - Date\n F- Hub Off\n  O - Hub on\n R - Remote desktop\n T - Wifi enable\n")
            client_socket.send("Z - Upload data\n")
    client_socket.close()
pisocket.close()
