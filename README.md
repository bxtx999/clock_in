# clock_in

定时打卡!

## 使用帮助

1. 开通腾讯云OCR服务

   参考[腾讯云OCR服务](https://cloud.tencent.com/document/product/866/34681)的文档，首先开通文字识别服务，然后在[API密钥管理](https://console.cloud.tencent.com/capi)中获取id与key。

2. 修改conf/settings.json中的相关设置。

   ```bash
     {
        "studentID": "",  # 学生id
        "password": "",   # 学生密码
        "province": "",   # 省，如 “湖南省”
        "city": "",       # 城市，如 “长沙市”
        "country": "",    # 区，如 “岳麓区”
        "address": "",    # 具体地址，如 “麓山南路2号”
        "SecretId": "",   # 腾讯云id
        "SecretKey": "",  # 腾讯云key
        "schedule": {
          "hour": 8,
          "minute": 20
         }
      }

   ```

3. 启动打卡任务（2种方式）

   - 在云服务器运行`python3 vps.py`定时每天8.20打卡，在github action中则每天6点左右进行打卡。

   - 使用github action服务，参考[《阮一峰_GitHub Actions 教程：定时发送天气邮件》](http://www.ruanyifeng.com/blog/2019/12/github_actions.html)。GitHub 只要发现配置文件，就会运行 Actions。

   在.github/workflows中修改`main.yml`文件内容。

## todo

1. 完善docker image构建。
