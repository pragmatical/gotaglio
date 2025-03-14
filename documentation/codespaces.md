# Using GitHub Codespaces

Go to the repo at [https://github.com/MikeHopcroft/gotaglio](https://github.com/MikeHopcroft/gotaglio)

Locate the green `Code` menu and choose the `Codespaces` tab. Press the `+` button to create a new Codespace based on this repo.

![](codespaces.png)

A browser tab will open with a remote web instance of Visual Studio Code, connected to a virtual machine in the cloud. It may take a few minutes for the environment to start.

You can click on the `Building codespace...` link in the lower right corner to see the devcontainer initialization process:
![](./building-codespace.png)

It pulls a bunch of container layers and then installs [PyPi](https://pypi.org/) dependencies.
![](./building-codespace2.png)

Here's the codespace, ready to go. You are ready to go with the built in model mocks.

![](./building-codespace3.png)

## Virtual Environment

The `gotaglio` codespace is configured to use a virtual environment in the `.venv` folder. The `~/.bashrc` should ensure the virtual environment is activated.

You can verify the virtual environment activation as follows:
~~~sh
if [[ -n "$VIRTUAL_ENV" ]]; then
    echo "Virtual environment is active: $VIRTUAL_ENV"
else
    echo "No virtual environment is active."
fi
~~~

If you run into import problems, check to see if the virtual environment is activated for your toolchain.
