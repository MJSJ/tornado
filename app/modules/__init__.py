#!/usr/bin/env python
# encoding: utf-8
"""
    __init__.py
    @author yf
    @version
    Copyright (c) 2013 yufeng All rights reserved.
"""
import tornado.web
import tornado.web, hmac, hashlib, datetime, json, time #, functools, urllib, os
from tornado.escape import json_decode
from tornado import escape
import decimal
import logging as l
import urllib, urllib2, json, hashlib

def _default(obj):
    if isinstance(obj, datetime.datetime):
        return obj.strftime('%Y-%m-%dT%H:%M:%S')
    elif isinstance(obj, datetime.date):
        return obj.strftime('%Y-%m-%d')
    elif isinstance(obj, decimal.Decimal):
        return str(obj)
    else:
        return obj

class base(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        uid = self.get_secure_cookie("u")
        u = self.db.user(id=uid).one()
        if u:
            return { 'id': unicode(u.id), "role": unicode(u.role), "name": unicode(u.username) }
        return None

    def write(self, chunk):
        if isinstance(chunk, dict):
            cb = self.get_argument("callback", None)
            if cb is not None:
                super(base, self).write(cb + '(' + json.dumps(chunk) + ')')
                self.set_header('Content-Type', 'application/javascript')
            else:
                chunk = json.dumps(chunk, default=_default).replace('</', "<\\/")
                self.set_header("Content-Type", "application/json; charset=UTF-8")
                chunk = escape.utf8(chunk)
                self._write_buffer.append(chunk)
        else:
            super(base, self).write(chunk)

    def hour(self, h=1):
        cur = datetime.datetime.now() - datetime.timedelta(minutes=int(h)*60)
        return "%d-%02d-%02d %02d:%02d:%02d" % (cur.year, cur.month, cur.day, cur.hour, cur.minute, cur.second)

    def set_default_headers(self):
        self.set_header('Server', 's')
        # debug CORS
        self.set_header('Access-Control-Allow-Origin', 'http://10.2.24.236:3000')
        self.set_header('Access-Control-Allow-Credentials', 'true')

    def json_decode(self, v):
        r = {}
        for ite in v.split("&"):
            vs = ite.split("=")
            if len(vs) == 2 and tornado.escape.url_unescape(vs[0]) != '_xsrf':
                r[tornado.escape.url_unescape(vs[0])] = tornado.escape.url_unescape(vs[1])
        return r
    
    def static_show(self, h):
        return h + '?v=' + str( int(time.time()) )

    @property
    def now(self):
        return datetime.datetime.now()

    def timest(self):
        return time.time()

    '''
    yf: 网站登录认证: 获取access_token
    '''
    def get_access_token(self, c):
        # if hasattr(self.application, "access_token") == False:
        url = "https://api.weixin.qq.com/sns/oauth2/access_token?appid=wxd0124a9e51032874&secret=a64c71252df6a6611e893c2ba53adf35&code="+c+"&grant_type=authorization_code"
        l.info(url)
        req = urllib2.Request(url)
        res_data = urllib2.urlopen(req)
        res = res_data.read()
        json_acceptable_string = res.replace("'", "\"")
        d = json.loads(json_acceptable_string)
        return d
        # else:
        #     if self.timest() - self.application.access_exp > 7200: # 过期了
        #         url = "https://api.weixin.qq.com/sns/oauth2/refresh_token?appid=wx2dbca94de092ab7f&grant_type=refresh_token&refresh_token="+self.application.refresh_token
        #         req = urllib2.Request(url)
        #         res_data = urllib2.urlopen(req)
        #         res = res_data.read()
        #         json_acceptable_string = res.replace("'", "\"")
        #         d = json.loads(json_acceptable_string)
        #         self.application.access_token = d["access_token"]
        #         self.application.refresh_token = d["refresh_token"]
        #         self.application.access_exp = self.timest()
        #         return d
        #     else: # 没有过期
        #         pass

    '''
    yf: 网站登录认证: 获取access_token
    '''
    def get_web_user(self, r):
        url = "https://api.weixin.qq.com/sns/userinfo?access_token="+r["access_token"]+"&openid="+r["openid"]+"&lang=zh_CN"
        req = urllib2.Request(url)
        res_data = urllib2.urlopen(req)
        res = res_data.read()
        json_acceptable_string = res.replace("'", "\"")
        d = json.loads(json_acceptable_string)
        return d

    '''
    yf: 公众号: 设置并保存token
    '''
    def check_tocken(self):
        if hasattr(self.application, "_appToken") == False:
            self.setToken(1)
            self.application._apptokenEx = self.timest()
        else:
            if self.timest() - self.application._apptokenEx > 7200:
                self.setToken(1)
                self.application._apptokenEx = self.timest()
            else:
                pass
        if hasattr(self.application, "_webToken") == False:
            self.setToken(2)
            self.application._webtokenEx = self.timest()
        else:
            if self.timest() - self.application._webtokenEx > 7200:
                self.setToken(2)
                self.application._webtokenEx = self.timest()
            else:
                pass

    '''
    yf: 公众号: 获取token
    '''
    def setToken(self, tp):
        urlweb = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wxd0124a9e51032874&secret=a64c71252df6a6611e893c2ba53adf35"
        urlapp = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wxd0124a9e51032874&secret=a64c71252df6a6611e893c2ba53adf35"
        if tp == 1:
            url = urlapp
        elif tp == 2:
            url = urlweb
        else:
            url = ""
        req = urllib2.Request(url)
        res_data = urllib2.urlopen(req)
        res = res_data.read()
        json_acceptable_string = res.replace("'", "\"")
        d = json.loads(json_acceptable_string)
        if d["access_token"] is not None:
            if tp == 1:
                self.application._appToken = d["access_token"]
            elif tp == 2:
                self.application._webToken = d["access_token"]
            else:
                pass
        else:
            pass

    '''
    yf: 公众号: 根据token获取user
    '''
    def getU(self):
        url = "https://api.weixin.qq.com/cgi-bin/user/get?access_token=" + self.application._webToken
        l.info(url)
        req = urllib2.Request(url)
        res_data = urllib2.urlopen(req)
        res = res_data.read()
        json_acceptable_string = res.replace("'", "\"")
        d = json.loads(json_acceptable_string)
        return d