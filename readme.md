# WebOBS

[![WebOBS](https://img.shields.io/badge/WebOBS-%40lWaterLite-blue)](https://github.com/lWaterLite) [![QUIC](https://img.shields.io/badge/QUIC-RFC%209000-blue)]([RFC 9000 - QUIC: A UDP-Based Multiplexed and Secure Transport (ietf.org)](https://datatracker.ietf.org/doc/html/rfc9000)) [![HTTP3](https://img.shields.io/badge/HTTP3-RFC%209114-blue)]([RFC 9114 - HTTP/3 (ietf.org)](https://datatracker.ietf.org/doc/html/rfc9114)) [![WebTransprot](https://img.shields.io/badge/WebTransport-draft03-green)]([WebTransport over HTTP/3 (ietf.org)](https://www.ietf.org/archive/id/draft-ietf-webtrans-http3-03.html))

一个基于HTTP3的轻量级实时流媒体传输系统

------

## 介绍

WebOBS是一个完全基于HTTP3协议传输的，轻量级的，即插即用的流媒体传输系统。客户端完全基于Web API实现。只需简单的几步配制，就能搭建一个简便的实时采集、监控平台。

*注意：本项目所使用的视频传输套件WebTranport截至2023.12.6仍处于草案阶段，甚至没有很好地被Chrome系支持。与此同时，受限于您所在地服务商的影响，QUIC与H3所构成的传输协议可能无法提供更好的网络服务甚至会使得效果更差。基于上述理由，不建议将此系统用于任何实际生产环境中，此项目仅作对于互联网前沿传输协议与套件的实验与探索，任何因项目所造成的影响都与开发者无关。*

------

## 安装与使用

### 先决条件

为了在公网上部署本项目，你必须拥有一台具有公网IP的服务器，以及一个具有证书的注册域名。如果使用范围仅限于内网，则无需上述条件。

### 安装

你可以简单的克隆main分支到本地。如果你不太了解Git是如何运作的，选择网页上的Code按钮下载压缩包到本地也是一种选择。

确保您的电脑已经正确安装Python，经过测试认为`Python3.10.8`及以上版本都可以正确运行本项目，不保证任何低于此版本的环境能够正常运行。如果您还没有安装Python，您可以前往[Download Python | Python.org](https://www.python.org/downloads/)选择最新的稳定版下载安装。

确保您的电脑中安装了最新版的Chrome，Edge在当前是不可接受的，其暂且无法正常接收所需的命令行参数以作启动。

完成上述检查后，在项目根目录打开终端，运行

```shell
pip install -r requirements.txt
```

确保安装pip安装进程正常退出无错误，如果安装过程发生了异常，重新运行上述命令只到正常运行完成。

接下来，将您的域名认证证书和密钥分别重命名为server.pem, server_key.pem，存放在项目的certifi文件夹下，覆盖原有密钥。

### 部署

完成上述步骤之后，在终端中运行

```shell
python main.py
```

这个脚本的所有参数都是可选的，其均被赋予了默认值

- `--host default='localhost'`: 服务器运行的主机
- `--prot default=4433`: 服务器运行的端口
- `--certifi_file default='./certifi/server.pem'`: 域名认证证书文件路径
- `--certifi_key default='./certifi/server_key.pem'`: 域名认证私钥文件路径
- `--log default='./log/sl_log.log'`: 加密日志文件，可以用于网络抓包工具分析
- `--retry default=False`: 设定服务器是否尝试重连

如果你不了解上述参数含义，使用默认值即可。

如果一切顺利，你应该可以在终端中看到服务器成果运行的日志。

### 使用

打开文本编辑器，将`OpenChrome.ps1`中的域名与端口更改成你在启动服务器时填写的内容。然后使用PowerShell运行此脚本。

现在Chrome应该本被正常唤起，你已经可以看到项目的index页面了。

现在你可以通过这个窗口输入URL访问项目提供的服务了，请注意对于服务的访问必须通过脚本所打开的窗口进行，任何直接的访问请求都因项目所使用的强制协议需求而被阻挡。

### API

`/` | `/index`

- 访问项目起始页。

`/wt/streamer`

- 访问捕获页面，这个页面用于捕获视频源并推流。

`/wt/receiver`

- 访问接收页面，这个页面用于拉取视频流并渲染。

`/wt/push`

- 用于使用WebTransport的UnidirectionalStream进行流推送，不能用于直接访问。

`/wt/get`

- 用于使用WebTransport的BidirectionalStream进行流确认和拉取，不能用于直接访问。

------

## 借物表

感谢这些Repo，文档与教程带给我的灵感和指导，没有它们就不会有这个项目

- [w3c/webtransport: WebTransport is a web API for flexible data transport (github.com)](https://github.com/w3c/webtransport)

- [w3c/webcodecs: WebCodecs is a flexible web API for encoding and decoding audio and video. (github.com)](https://github.com/w3c/webcodecs)

- [aiortc/aioquic: QUIC and HTTP/3 implementation in Python (github.com)](https://github.com/aiortc/aioquic)

- [RFC 9114 - HTTP/3 (ietf.org)](https://datatracker.ietf.org/doc/html/rfc9114)

- [RFC 9000 - QUIC: A UDP-Based Multiplexed and Secure Transport (ietf.org)](https://datatracker.ietf.org/doc/html/rfc9000)

- [RFC 9114 - HTTP/3 (ietf.org)](https://datatracker.ietf.org/doc/html/rfc9114)

- [draft-ietf-webtrans-http3-08 - WebTransport over HTTP/3](https://datatracker.ietf.org/doc/draft-ietf-webtrans-http3/)

- [WebCodecs API - Web APIs | MDN (mozilla.org)](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API)

- [WebTransport - Web APIs | MDN (mozilla.org)](https://developer.mozilla.org/en-US/docs/Web/API/WebTransport)

  以及各式各样的于CSDN，StackOverflow, Reddit, 知乎等平台上发布的帖子。

------

## 开源许可

