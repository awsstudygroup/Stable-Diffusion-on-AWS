## 安全验证

所有 API 使用 API 密钥进行安全验证，所有 API 请求都应在 HTTP 标头中包含您的 API 密钥，`x-api-key` 如下所示：

```config
x-api-key: xxxxxxxxxxxxxxxxxxxx
```

## 用户验证

请在 HTTP 标头中包含 `username`，例如，如果在 WebUI 上配置的用户名是 `admin`，则：

```config
username: admin
```

> API 部署完成后，会内置名为 `api` 的用户，如果您不使用 WebUI 进行初始化或者没有通过 API 创建新的用户，可使用 `api` 作为用户名。

## 1.4.0 或更低版本

应在 HTTP 标头中包含 `Authorization`，如下所示：

```config
Authorization: Bearer {TOKEN}
```

Token 算法（Python 示例）：

```python
import base64

username = "your username on webui"
token = base64.b16encode(username.encode("utf-8")).decode("utf-8")
```

例如，如果在 WebUI 上配置的用户名是 `admin`，则：

```config
Authorization: Bearer 61646D696E
```
