import os
import json
import time
import pytz
import requests
import argparse
import datetime
from halo import Halo
from retrying import retry
from gettext import gettext as _
from typing import Dict, Optional
from apscheduler.schedulers.blocking import BlockingScheduler

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ocr.v20181119 import ocr_client, models

HNU_ClockIn = {
    'login_url': 'https://fangkong.hnu.edu.cn/api/v1/account/login',
    'get_token': 'https://fangkong.hnu.edu.cn/api/v1/account/getimgvcode',
    'token_image': 'https://fangkong.hnu.edu.cn/imagevcode?token={0}',
    'clock_in': 'https://fangkong.hnu.edu.cn/api/v1/clockinlog/add'
}


def imageToCode(token: str, secret_id: str, secret_key: str):
    try:
        cred = credential.Credential(secret_id, secret_key)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "ocr.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = ocr_client.OcrClient(cred, "ap-beijing", clientProfile)

        req = models.GeneralAccurateOCRRequest()
        params = {
            "ImageUrl": HNU_ClockIn["token_image"].format(token)
        }
        req.from_json_string(json.dumps(params))

        resp = client.GeneralAccurateOCR(req)
        return json.loads(resp.to_json_string())  # ['Response']['TextDetections']['DetectedText']

    except TencentCloudSDKException as err:
        print(err)


def _read_settings(settings: str = "settings.json"):
    with open(settings, 'r') as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(e)
            pass
        return data


class Sign:
    session: Optional[requests.Session]
    login_payload: Dict
    add_payload: Dict
    max_retry: int = 5
    username: Optional[str]
    password: Optional[str]
    province: Optional[str]
    city: Optional[str]
    country: Optional[str]
    address: Optional[str]
    secret_id: Optional[str]
    secret_key: Optional[str]
    token: Optional[str]
    vercode: Optional[str]
    spinner = Halo(text="Loading", spinner='dots')

    def __init__(self, **kwargs):
        self.session = requests.Session()
        self.secret_id = kwargs.get("secretId", None)
        self.secret_key = kwargs.get("secretKey", None)
        if not all([self.secret_id, self.secret_key]):
            print("secretId: {} and secretKey {} error.".format(self.secret_id, self.secret_key))
            exit()
        self.username = kwargs.get("studentID")
        self.password = kwargs.get("password")
        self.province = kwargs.get("province")
        self.city = kwargs.get("city")
        self.country = kwargs.get("country")
        self.address = kwargs.get("address")
        if not all([self.username, self.password, self.province, self.city, self.country, self.address]):
            print("Config Error.")
            exit()
        self.spinner.start('正在新建打卡实例...')
        self.spinner.succeed('已新建打卡实例')
        self.spinner.start(text="正在访问到湖南大学打卡平台")

    def login(self) -> bool:
        max_retry = 0
        self.spinner.start(text="正在尝试为您登录系统，获取Token..\n")
        while max_retry < self.max_retry:
            try:
                r = self.session.post(url=HNU_ClockIn["login_url"], json=self._get_login_payload(),
                                      headers=self._get_header())
                if r.status_code != 200:
                    raise HTTPError
                self.spinner.succeed(text="登录成功！")
                return True
            except Exception as e:
                print("登录错误， ErrorCode: {}".format(e))
                self.spinner.fail(text="3秒后重新尝试！")
                time.sleep(3)
            max_retry += 1

    def add(self):
        self.spinner.start(text="正在为您打卡...")
        max_retry = 0
        while max_retry < self.max_retry:
            try:
                r = self.session.post(url=HNU_ClockIn["clock_in"], json=self._get_add_payload(),
                                      headers=self._get_header())
                try:
                    r.json()
                except Exception as e:
                    continue
                if r.json()['code'] == 1:
                    self.spinner.stop_and_persist(symbol='🦄 '.encode('utf-8'), text='您今天已经提交过打卡信息。')
                    break
                elif r.json()['code'] == 0:
                    self.spinner.stop_and_persist(symbol='🦄 '.encode('utf-8'), text='已为您打卡成功！')
                    break
                else:
                    self.spinner.stop_and_persist(symbol='🦄 '.encode('utf-8'), text='提交信息错误！')
                    raise AddError
            except AddError as e:
                self.spinner.fail(text="3秒后尝试为您重新打卡！")
                time.sleep(3)
            max_retry += 1
        if max_retry >= self.max_retry:
            return False
        return True

    def _get_add_payload(self) -> Dict:
        return {
            "Temperature": None,
            "RealProvince": self.province,
            "RealCity": self.city,
            "RealCounty": self.country,
            "RealAddress": self.address,
            "IsUnusual": "0",
            "UnusualInfo": "",
            "IsTouch": "0",  # 是否接触
            "IsInsulated": "0",
            "IsSuspected": "0",
            "IsDiagnosis": "0",
            "tripinfolist": [
                {
                    "aTripDate": "",
                    "FromAdr": "",
                    "ToAdr": "",
                    "Number": "",
                    "trippersoninfolist": []
                }
            ],
            "toucherinfolist": [],
            "dailyinfo": {
                "IsVia": "0",
                "DateTrip": ""
            },
            "IsInCampus": "0",
            "IsViaHuBei": "0",
            "IsViaWuHan": "0",
            "InsulatedAddress": "",
            "TouchInfo": "",
            "IsNormalTemperature": "1",
            "Longitude": None,
            "Latitude": None
        }

    def _get_login_payload(self) -> Dict:
        self.get_code()
        return {
            "Code": self.username,
            "Password": self.password,
            "Token": self.token,
            "VerCode": self.vercode,
            "WechatUserinfoCode": None
        }

    def _get_header(self) -> Dict:
        return {
            "Host": "fangkong.hnu.edu.cn",
            "Origin": "https://fangkong.hnu.edu.cn",
            "Referer": "https://fangkong.hnu.edu.cn/app/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0"
        }

    def _get_token(self):
        max_retry = 0
        while max_retry < self.max_retry:
            try:
                r = self.session.get(url=HNU_ClockIn["get_token"], headers=self._get_header())
                if r.status_code == 200 and r.json()["msg"] == "成功":
                    self.token = r.json()["data"]["Token"]
                    break
                else:
                    raise ValueError
            except Exception as e:
                print(e)
                time.sleep(3)
            max_retry += 1


    def get_code(self):
        max_retry = 0
        cod = None
        while max_retry < self.max_retry:
            self._get_token()
            if not self.token:
                print("Token Error.")
                time.sleep(3)
                continue
            try:
                cod = imageToCode(self.token, self.secret_id, self.secret_key)["TextDetections"][0]["DetectedText"]
                if not cod.isdigit():
                    raise ValueError
                self.vercode = cod
                self.spinner.succeed('获取token {0} 和验证码 {1}'.format(self.token, self.vercode))
                break
            except ValueError as e:
                print("Token: {}, 验证码识别为：{}。发现错误! 3秒后为您尝试！", self.token, cod)
                time.sleep(3)
            max_retry += 1


class VersionedHelp(argparse.HelpFormatter):
    def _format_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = _('Version: x.y\n\nusage: ')
        return argparse.HelpFormatter._format_usage(self, usage, actions, groups, prefix)


def parse():
    parser = argparse.ArgumentParser(formatter_class=VersionedHelp)
    parser.add_argument("--province", "-a", type=str, help="所在省份", default="湖南省")
    parser.add_argument("--city", "-b", type=str, help="所在城市", default="长沙市")
    parser.add_argument("--country", "-c", type=str, help="所在区县", default="岳麓区")
    parser.add_argument("--address", "-d", type=str, help="具体地址", default="湖南大学软件大楼")
    parser.add_argument("--username", "-s", type=str, help="学号")
    parser.add_argument("--password", "-p", type=str, help="密码")
    parser.add_argument("--hour", "-t", type=int, default=9, help="打卡时间")
    parser.add_argument("--minute", "-m", type=int, default=20, help="打卡时间")
    parser.add_argument("--secretid", "-i", type=str, help="腾讯云密钥id")
    parser.add_argument("--secretkey", "-k", type=str, help="腾讯云密钥key")
    return parser.parse_args()


# Exceptions
class LoginError(Exception):
    """Login Error"""
    pass


class TokenError(Exception):
    """Token Error"""
    pass


class HTTPError(Exception):
    """HTTP Error"""
    pass


class AddError(Exception):
    """Add Error"""
    pass


def schedule(**kwargs):
    scheduler = BlockingScheduler()
    scheduler.add_job(main, 'cron', args=[kwargs], hour=kwargs["hour"], minute=kwargs["minute"])
    print('⏰ 已启动定时程序，每天 {0}:{1} 为您打卡'.format(kwargs["hour"], kwargs["minute"]))
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
    return scheduler


def main(**kwargs):
    """
     main function.
     kwargs:
        "studentID": studentID,
        "password": password,
        "province": province,
        "city": city,
        "country": country,
        "address": address,
        "hour": hour,
        "minute": minute
    """
    # SET time-zone
    print('[Time] {}'.format(datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))))
    print('🚌 打卡任务启动')

    max_try = 0
    while max_try < 5:
        print("第{}次尝试为您打卡！".format(max_try + 1))
        s = Sign(**kwargs)
        # 登录
        s.login()
        # 打卡
        status = s.add()
        if status:
            break
        s.spinner.fail("打开失败，稍后会自动尝试！")
        time.sleep(20)
        del s
        max_try += 1


def get_config() -> Dict:
    if os.access("/opt/conf/settings.json", os.F_OK) and os.access("/opt/sign/settings.json", os.R_OKR_OK):
        print("正在使用 /opt/conf/settings.json 中的配置\n")
        config = json.loads(open('/opt/conf/settings.json', 'r').read())
        studentID = config["studentID"]
        password = config["password"]
        province = config["province"]
        city = config["city"]
        country = config["country"]
        address = config["address"]
        hour = config["schedule"]["hour"] or 9
        minute = config["schedule"]["minute"] or 20
        SecretId = config["SecretId"]
        SecretKey = config["SecretKey"]
    elif os.path.exists('settings.json'):
        print("正在使用 settings.json 中的配置\n")
        config = json.loads(open('./settings.json', 'r').read())
        studentID = config["studentID"]
        password = config["password"]
        province = config["province"]
        city = config["city"]
        country = config["country"]
        address = config["address"]
        hour = config["schedule"]["hour"] or 9
        minute = config["schedule"]["minute"] or 20
        SecretId = config["SecretId"]
        SecretKey = config["SecretKey"]
    else:
        args = parse()
        studentID = args.username
        password = args.password
        province = args.province
        city = args.city
        country = args.country
        address = args.address
        hour = args.hour
        minute = args.minute
        SecretId = args.secretid
        SecretKey = args.secretkey
    return {
        "studentID": studentID,
        "password": password,
        "province": province,
        "city": city,
        "country": country,
        "address": address,
        "hour": hour,
        "minute": minute,
        "secretId": SecretId,
        "secretKey": SecretKey
    }
