# clock_in

定时打卡!

## 使用帮助

1. 开通腾讯云OCR服务

   参考[腾讯云OCR服务](https://cloud.tencent.com/document/product/866/34681)的文档，首先开通文字识别服务，然后在[API密钥管理](https://console.cloud.tencent.com/capi)中获取id与key。

2. 修改settings.json中的相关设置。

3. 在云服务器运行`python3 vps.py`定时每天8.20打卡，在github action中则每天凌晨进行打卡。

4. 使用github action服务，参考[《阮一峰_GitHub Actions 教程：定时发送天气邮件》](http://www.ruanyifeng.com/blog/2019/12/github_actions.html)。GitHub 只要发现配置文件，就会运行 Actions。

   在.github/workflows中修改`main.yml`文件内容。

## todo

1. 完善docker image构建。
