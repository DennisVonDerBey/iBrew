# -*- coding: utf8 -*-


from datetime import date
import tornado.escape
import tornado.ioloop
import tornado.web
import socket
import time

import os
from smarter.SmarterClient import *

from iBrewBonjour import *
from iBrewJokes import *

#------------------------------------------------------
# SMARTER PROTOCOL INTERFACE REST API
#
# REST API interface to iKettle 2.0 & SmarterCoffee Devices
#
# https://github.com/Tristan79/iBrew
#
# Copyright © 2016 Tristan (@monkeycat.nl)
#
# Brewing on the 7th day (rev 6)
#------------------------------------------------------





def custom_get_current_user(handler):
    #user = handler.get_secure_cookie("user")
    #if user:
    user = "#NONE#"
    return user


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return custom_get_current_user(self)



class GenericAPIHandler(BaseHandler):
    def validateAPIKey(self):
        api_key = self.get_argument(u"apikey", default="")
        if api_key == "APIKEY":
            return True
        else:
            raise tornado.web.HTTPError(400)
            return False

#------------------------------------------------------
# WEB GUI PAGES
#------------------------------------------------------

webroot = "web/"

class GenericPageHandler(BaseHandler):
    #@tornado.web.authenticated
    def get(self,page):
        if os.path.isfile(os.path.join(os.path.dirname(__file__), webroot)+page+".html"):
            self.render(webroot+page+".html")
        else:
            self.render(webroot+"somethingwrong.html")


class WebMainHandler(BaseHandler):
    #@tornado.web.authenticated
    def get(self):
        d = dict()
        for ip in self.application.clients:
            client = self.application.clients[ip]
            d.update({client.host : Smarter.device_to_string(client.deviceId)})
        self.render(webroot+"index.html",devices = d,joke = iBrewJokes().joke())


class WebAPIHandler(BaseHandler):
    #@tornado.web.authenticated
    def get(self):
        d = dict()
        for ip in self.application.clients:
            client = self.application.clients[ip]
            d.update({client.host : Smarter.device_to_string(client.deviceId)})
        self.render(webroot+"api.html",devices = d,joke = iBrewJokes().joke())


class WebDeviceHandler(BaseHandler):
    #@tornado.web.authenticated
    def get(self,ip):
        if ip in self.application.clients:
            c = self.application.clients[ip]
            self.render(webroot+"device.html",client = c)
        else:
            self.render(webroot+"somethingwrong.html")


class WebSettingsHandler(BaseHandler):
    #@tornado.web.authenticated
    def get(self,ip):
        if ip in self.application.clients:
            c = self.application.clients[ip]
            self.render(webroot+"settings.html",client = c)
        else:
            self.render(webroot+"somethingwrong.html")



#------------------------------------------------------
# REST PAGES
#------------------------------------------------------

#------------------------------------------------------
# Devices Handler
#------------------------------------------------------


def encodeFirmware(device,version):
    return { 'version'   : version, 'certified' : Smarter.firmware_verified(device,version) }


def encodeDevice(device,version):
    return { 'id'          : device,
             'type'        : Smarter.device_to_string(device),
            }


class DeviceHandler(tornado.web.RequestHandler):
    def get(self, ip):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            if client.isKettle:
                response = { 'device'      : encodeDevice(client.deviceId,client.version),
                             'firmware'    : encodeFirmware(client.deviceId,client.version),
                             'connected'   : client.connected,
                             'sensors'     : { 'watersensor' : { 'level'  : client.waterSensor,
                                                                 'base'   : client.waterSensorBase
                                                               },
                                               'offbase'     : not client.onBase,

                                               'temperature' : { 'fahrenheid' : Smarter.celcius_to_fahrenheid(client.temperature),
                                                                 'celcius   ' : client.temperature
                                                               }
                                             },
                             'status'      : { 'message' : Smarter.status_kettle_description(client.kettleStatus),
                                               'id'          : client.kettleStatus
                                             },
                             'default'     : { 'temperature' : { 'fahrenheid' : Smarter.celcius_to_fahrenheid(client.defaultTemperature),
                                                                 'celcius   ' : client.defaultTemperature
                                                               },
                                               'keepwarm'    : client.defaultKeepWarmTime,
                                               'formula'     : { 'use'     : client.defaultFormula,
                                                                 'temperature' : { 'fahrenheid' : Smarter.celcius_to_fahrenheid(client.defaultFormulaTemperature),
                                                                                   'celcius   ' : client.defaultFormulaTemperature
                                                                                 }

                                                               }
                                             }
                            }
            elif client.isCoffee:
                response = { 'device'      : encodeDevice(client.deviceId,client.version),
                             'firmware'    : encodeFirmware(client.deviceId,client.version),
                             'connected'   : client.connected,
                             'status'      : { 'message' : Smarter.status_coffee_description(client.coffeeStatus),
                                               'id'          : client.kettleStatus
                                             },
                             'sensors'     : { 'cups'       : client.cups,
                                               'strength'   : client.strength,
                                               'grinder'    : client.grinder,
                                               'hotplate'   : client.hotplate,
                                               'singlecup'  : client.singlecup,
                                               'carafe'     : client.carafe,
                                               'waterlevel' : client.waterLevel
                                             },
                             'default'     : { 'cups'       : client.defaultCups,
                                               'strength'   : client.defaultStrength,
                                               'grinder'    : client.defaultGrinder,
                                               'hotplate'   : client.defaultHotplate
                                              }
                            }


        else:
            response = { 'error': 'no device' }
        self.write(response)


class DevicesHandler(tornado.web.RequestHandler):
    def get(self):
        devices = SmarterClient().find_devices()
        response = {}
        for device in devices:
            response[device[0]] = encodeDevice(device[1],device[2])
        self.write(response)


class UnknownHandler(tornado.web.RequestHandler):
    def get(self):
        response = { 'error' : { 'code' : '0', 'message' : 'Request unavailable' }}
        self.write(response)



#------------------------------------------------------
# Kettle calibration
#------------------------------------------------------


class CalibrateHandler(tornado.web.RequestHandler):
    def get(self,ip):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            if client.isKettle:
                client.calibrate()
                response = { 'base'            : client.waterSensorBase,
                             'command status'  : client.commandStatus }
                self.write(response)
            else:
                response = { 'error': 'need kettle' }
        else:
            response = { 'error': 'no device' }


class CalibrateBaseHandler(tornado.web.RequestHandler):
    def get(self,ip):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            if client.isKettle:
                client.calibrate_base()
                response = { 'base'            : client.waterSensorBase,
                             'command status'  : client.commandStatus }
                self.write(response)
            else:
                response = { 'error': 'need kettle' }
        else:
            response = { 'error': 'no device' }


class CalibrateStoreBaseHandler(tornado.web.RequestHandler):
    def get(self,ip,base):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            if client.isKettle:
                client.calibrate_store_base(Smarter.string_to_watersensor(base))
                response = { 'base'            : client.waterSensorBase,
                             'command status'  : client.commandStatus }
            else:
                response = { 'error': 'need kettle' }
        else:
            response = { 'error': 'no device' }
        self.write(response)



#------------------------------------------------------
# Wifi operation
#------------------------------------------------------


class WifiScanHandler(tornado.web.RequestHandler):
    def get(self,ip):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            client.wifi_scan()
            networks = {}
            for i in range(0,len(client.Wifi)):
                networks.update( { client.Wifi[i][0] :
                                            { 'signal'  : str(client.Wifi[i][1]),
                                              'quality' : Smarter.dbm_to_quality(int(client.Wifi[i][1]))
                                            }
                                  } )
            response = { 'networks ': networks }
        else:
            response = { 'error': 'no device' }
        self.write(response)


class WifiJoinHandler(tornado.web.RequestHandler):
    def get(self,ip,name,password):
        if ip in self.application.clients:
            self.application.clients[ip].wifi_join(name,password)
            response = { 'success': 'joining wireless network' }
        else:
            response = { 'error': 'no device' }
        self.write(response)


class WifiLeaveHandler(tornado.web.RequestHandler):
    def get(self,ip):
        if ip in self.application.clients:
            self.application.clients[ip].wifi_leave()
            response = { 'success': 'left wireless network' }
        else:
            response = { 'error': 'no device' }
        self.write(response)



#------------------------------------------------------
# Settings
#------------------------------------------------------


class StoreSettingsHandler(tornado.web.RequestHandler):
    def get(self,ip,x1,x2,x3,x4):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            client.device_store_settings(x1,x2,x3,x4)
            response = { 'command status'  : client.commandStatus }
        else:
            response = { 'error': 'no device' }
        self.write(response)


class SettingsHandler(tornado.web.RequestHandler):
    def get(self,ip):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            client.device_settings()
            response = { 'command status'  : client.commandStatus }
        else:
            response = { 'error': 'no device' }
        self.write(response)


class SettingsDefaultHandler(tornado.web.RequestHandler):
    def get(self,ip):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            client.device_default()
            response = { 'command status'  : client.commandStatus }
        else:
            response = { 'error': 'no device' }
        self.write(response)


#------------------------------------------------------
# Coffee settings
#------------------------------------------------------

class StrengthHandler(tornado.web.RequestHandler):
    def get(self,ip,strength):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            if client.isCoffee:
                client.coffee_strength(strength)
                response = { 'command status'  : client.commandStatus }
            else:
                response = { 'error': 'need coffee machine' }
        else:
            response = { 'error': 'no device' }
        self.write(response)


class CupsHandler(tornado.web.RequestHandler):
    def get(self,ip,cups):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            if client.isCoffee:
                client.coffee_strength(strength)
                response = { 'command status'  : client.commandStatus }
            else:
                response = { 'error': 'need coffee machine' }
        else:
            response = { 'error': 'no device' }
        self.write(response)


class GrinderHandler(tornado.web.RequestHandler):
    def get(self,ip,bool):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            if client.isCoffee:
                client.coffee_grinder(bool)
                response = { 'command status'  : client.commandStatus }
            else:
                response = { 'error': 'need coffee machine' }
        else:
            response = { 'error': 'no device' }
        self.write(response)


class HotPlateHandler(tornado.web.RequestHandler):
    def get(self,ip,timer):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            if client.isCoffee:
                client.coffee_cups(timer)
                response = { 'command status'  : client.commandStatus }
            else:
                response = { 'error': 'need coffee machine' }
        else:
            response = { 'error': 'no device' }
        self.write(response)


class CarafeHandler(tornado.web.RequestHandler):
    def get(self,ip):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            if client.isCoffee:
                client.coffee_carafe()
                response = { 'carafe'         : client.carafe,
                             'command status' : client.commandStatus }
            else:
                response = { 'error': 'need coffee machine' }
        else:
            response = { 'error': 'no device' }
        self.write(response)


class SingleCupHandler(tornado.web.RequestHandler):
    def get(self,ip):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            if client.isCoffee:
                client.coffee_singlecup()
                response = { 'singlecup'      : client.singlecup,
                             'command status' : client.commandStatus }
            else:
                response = { 'error': 'need coffee machine' }
        else:
            response = { 'error': 'no device' }
        self.write(response)



#------------------------------------------------------
# STOP START COMMANDS
#------------------------------------------------------


class StopHandler(tornado.web.RequestHandler):
    def get(self,ip):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            client.device_stop()
            response = { 'command status' : client.commandStatus }
        else:
            response = { 'error': 'no device' }
        self.write(response)


class StartHandler(tornado.web.RequestHandler):
    def get(self,ip):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            client.device_start()
            response = { 'command status' : client.commandStatus }
        else:
            response = { 'error': 'no device' }
        self.write(response)



class SSStopHandler(tornado.web.RequestHandler):
    def get(self,ip):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            client.device_stop()


class SSStartHandler(tornado.web.RequestHandler):
    def get(self,ip):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            client.device_start()



#------------------------------------------------------
# Misc
#------------------------------------------------------


class JokeHandler(tornado.web.RequestHandler):
    def get(self,ip=""):
        if ip in self.application.clients:
            client = self.application.clients[ip]
            if   client.isCoffee: joke = iBrewJokes().coffee()
            elif client.isKettle: joke = iBrewJokes().tea()
            response = { 'joke' :  { 'question' : joke[0] , 'answer' : joke[1] }}
        elif ip == "":
            joke = iBrewJokes().joke()
            response = { 'joke' :  { 'question' : joke[0] , 'answer' : joke[1] }}
        else:
            response = { 'error': 'no device' }
        self.write(response)



class VersionHandler(tornado.web.RequestHandler):
    def get(self):
        response = { 'description': 'iBrew Smarter REST API',
                     'version'    : self.application.version,
                     'copyright'  : { 'year'   : '2016',
                                      'holder' : 'Tristan Crispijn'
                                    }
                    }
        self.write(response)



#------------------------------------------------------
# REST INTERFACE
#------------------------------------------------------


class iBrewWeb(tornado.web.Application):

    version = '0.2'
    
    def start(self):
        tornado.ioloop.IOLoop.instance().start()
    
    def run(self):
        import threading
        t = threading.Thread(target=self.start)
        t.start()


    def kill(self):
    
        for ip in self.clients:
            self.clients[ip].disconnect()
        
        deadline = time.time() + 3
        io_loop = tornado.ioloop.IOLoop.instance()
     
        def stop_loop():
            now = time.time()
            if now < deadline and (io_loop._callbacks or io_loop._timeouts):
                io_loop.add_timeout(now + 1, stop_loop)
            else:
                io_loop.stop()
    
        stop_loop()
 
 
    def __init__(self,port,dump=False,host=""):
        self.port = port
        
        devices = SmarterClient().find_devices()
        self.clients = dict()
        
        for device in devices:
            client = SmarterClient()
            client.dump = dump
            if dump:
                client.dump_status = True
            client.host = device[0]
            client.init_default()
            self.clients[device[0]] = client
            print "iBrew Web Server: " + client.string_connect_status()
        
        if host != "":
            ip = socket.gethostbyname(host)
            print host
            print ip
            print self.application.clients
            if not ip in self.application.clients:
                client = SmarterClient()
                client.host = host
                client.dump = dump
                if dump:
                    client.dump_status = True
                client.init_default()
                self.clients[ip] = client
                print "iBrew Web Server: " + client.string_connect_status()

        try:
            self.listen(self.port, no_keep_alive = True)
        except:
            print  "iBrew Web Server: Couldn't open socket on port" + str(self.port)
        

        settings = {
                "debug": True,
                "static_path": os.path.join(os.path.dirname(__file__), "web/static")
            }

        handlers = [
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/status/?",DeviceHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/calibrate/?",CalibrateHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/calibrate/base/?",CalibrateBaseHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/calibrate/base/([0-9]+)/?",CalibrateStoreBaseHandler),
            
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/carafe/?",CarafeHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/singlecup/?",SingleCupHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/hotplate/([0-9]+)/?",HotPlateHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/cups/([0-9]+)/?",CupsHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/grinder/?",GrinderHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/strength/(weak|normal|strong)/?",StrengthHandler),
            
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/scan/?",WifiScanHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/join/(.+)/(.*)/?",WifiJoinHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/leave/?",WifiLeaveHandler),
            
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/start/?",StartHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/stop/?",StopHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/joke/?",JokeHandler),
            
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/settings/?",SettingsHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/default/?",SettingsDefaultHandler),
            (r"/api/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/settings/([0-9]+)/([0-9]+)/([0-9]+)/([0-9]+)/?",StoreSettingsHandler),
            
            (r"/api/version/?",           VersionHandler),
            (r"/api/devices/?",           DevicesHandler),
            (r"/api/joke/?",              JokeHandler),
            (r"/api/?",                   WebAPIHandler),
            (r"/api/?.*",                 UnknownHandler),
            (r"/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/?",WebDeviceHandler),
            (r"/([0-9]+.[0-9]+.[0-9]+.[0-9]+)/settings/?",WebSettingsHandler),
   
            (r"/",                        WebMainHandler),
                 #(r"/login",             LoginHandler),
            (r"/(.*)",                    GenericPageHandler),

            
        ]

        tornado.web.Application.__init__(self, handlers, **settings)
        
    #    bonjour = iBrewBonjourThread(self.port)
    #    bonjour.start()
