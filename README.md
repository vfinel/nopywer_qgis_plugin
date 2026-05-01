This is a QGIS plugin to use [nopywer](https://github.com/vfinel/nopywer) directly inside QGIS.

# installation 
- Open QGIS.
- Go to Plugins > Manage and Install Plugins... > Settings > "Plugin Repositories" > Add....
    - Name it whatever you like (e.g., "Nopywer Release Repo").
    - For the URL, paste this exact link: https://github.com/vfinel/nopywer_qgis_plugin/releases/latest/download/plugins.xml
        - /!\ make to remove the `http://` prefix already written, you need `https://` /!\ 
        - if you see the message `Unable to Get Local Issuer Certificate: The issuer certificate of a locally looked up certificate could not be found` you can click `Ignore`
    - close the `Settings` panel 

- Go to Plugins > Manage and Install Plugins... > All
    - search for `nopywer` plugin and install it 

# usage 

## prepapre your layers 
Make sure that your layers have the following properties:
- each features of nodes layers must have the following attributes:
    - `name`: a string describing the name of the load 
    - `power`: power usage of this node (it can be 0 if the node is not using power. Units can be in watts, kilowatts, or megawatts)
    - `phase`: the phase this node should draw power from (1, 2, 3, or T)

## run analysis 
- open the plugin 
- select your layers (nodes layer(s) and cable layer(s))
- click "Run analysis" 

## see nopywer logs 
Logs are visible in two places: 
- Log Messages Panel: Go to View -> Panels -> Log Messages (or click the speech bubble in the bottom right corner of QGIS) and select the "Nopywer" tab.
- QGIS Python Console: It will print a formatted block with the nopywer output.

This will show you exactly what nopywer is calculating, any warnings it generates, and the final result!


