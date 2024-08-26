 The following help you to fix errors or problems that you might encounter when using Extension for Stable Diffusion on AWS.

 **Error: It presents error message 'RuntimeError: "LayerNormKernelImpl" not implemented for 'Half'' when I use txt2img inference function**

The error appears when deploying webUI frontend. It's recommended to start webUI adding `--precision full --no-half`
```
./webui.sh --skip-torch-cuda-test --precision full --no-half
```


**Error: I cannot install python venv on Ubuntu using `python3 -m venv env`**

The error comes out when your system's default is Python 3.9, and Ubuntu 20.04 is Python 3.8. User can install venv package using `sudo apt install python3.8-venv` to explicitly mentioning the full version of Python.


**Error： When using the webUI, an Error prompt appears in the top right corner**

It is likely to be a connection error, indicating that the open-source webUI project has crashed. You can manually restart the webUI to resolve this issue. It's recommended to use the **Restart webUI** button for manual restart. 
![Restart webUI](./images/restart_UI.png)

