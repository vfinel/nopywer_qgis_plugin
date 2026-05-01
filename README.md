This is a QGIS plugin to use [nopywer](https://github.com/vfinel/nopywer) directly inside QGIS.

# installation 
- Open QGIS.
- Add nopywer plugin repositoey to QGIS Plugin Manager: Go to: *Plugins > Manage and Install Plugins... > Settings > "Plugin Repositories" > Add...*
    - Choose a name (e.g., "Nopywer Release Repo").
    - For the URL, paste this exact link: https://github.com/vfinel/nopywer_qgis_plugin/releases/latest/download/plugins.xml
        - /!\ make sure to remove the `http://` prefix already written, you need `https://` instead
        - if you see the message `Unable to Get Local Issuer Certificate: The issuer certificate of a locally looked up certificate could not be found` you can click `Ignore`

- Go to: *Plugins > Manage and Install Plugins... > All*
    - search for `nopywer` plugin 
    - install it 
    
    Note that the installation can take some time (about 1 minute), and multiple command windows may open. **Do not attempt to interact with QGIS during the installaton.**


# usage 

Once the installation is complete, you are ready to use nopywer!
 You can click on the nopywer plugin icon ![Nopywer Icon](nopywer_plugin/icon.png)

You can also open the plugin by going on *Plugins > nopywer*.

## prepare your layers 
Make sure that your layers have the following properties:
- each features of nodes layers must have the following attributes:
    - `name`: a string describing the name of the load 
    - `power`: power usage of this node (it can be 0 if the node is not using power. Units can be in watts, kilowatts, or megawatts)
    - `phase`: the phase this node should draw power from (1, 2, 3, or T)

## run analysis 
- open the plugin 
- select your layers (nodes layer(s) and cable layer(s))
- click `Run analysis`

## see nopywer logs 
Logs are visible in two places: 
- Log Messages Panel: Go to View -> Panels -> Log Messages (or click the speech bubble in the bottom right corner of QGIS) and select the "Nopywer" tab.
- QGIS Python Console: Go to Plugins -> Python console (or Ctrl + Alt + P)

This will show you exactly what nopywer is calculating, any warnings it generates, and the final result!


