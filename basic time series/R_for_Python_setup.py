#!/usr/bin/env python3
#
# Martin Burda, University of Toronto
#
#--------------------------------------------------------------------------------------------------
def set_env_Win_macOS():

    import os, sys, platform
    os_name = platform.system()

    if os_name == 'Windows':
        os.environ["R_HOME"] = os.path.join(os.environ['CONDA_PREFIX'], 'Lib', 'R')
        os.environ["PATH"] = os.pathsep.join([
            os.environ["PATH"],
            os.path.join(os.environ['CONDA_PREFIX'], 'Lib', 'R', 'bin', 'x64')
        ])
    elif os_name == 'Darwin':
        os.environ["R_HOME"] = os.path.join(os.environ['CONDA_PREFIX'], 'lib', 'R')
        os.environ["PATH"] = os.pathsep.join([
            os.environ["PATH"],
            os.path.join(os.environ['CONDA_PREFIX'], 'lib', 'R', 'bin')
        ])
    else:
        print(f"In RPY.set_env_Win_macOS, unsupported OS: {os_name}")
        sys.exit(1)

    return

#--------------------------------------------------------------------------------------------------
def install_R():

    import os, sys, subprocess, importlib
    IN_ANACONDA = 'CONDA_DEFAULT_ENV' in os.environ      

    if IN_ANACONDA:    
       
        # Set environment variables R_HOME and PATH for R in Python
        set_env_Win_macOS()
     
        # Conda system packages to check and install if necessary
        sys_packages = ['r-essentials']
        
        for package in sys_packages:
            # Check if the conda system package is installed
            sys_list_result = subprocess.run(
                ['conda', 'list', package], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if package not in sys_list_result.stdout:
                # Package is not installed, install it
                print(f"Installing {package}...")
                subprocess.check_call(['conda', 'install', '--yes', package])
            else:
                print(f"{package} is already installed.")        

    else:
        print(f"In RPY.install_R, unsupported Development tool")
        sys.exit(1)

    return 

#--------------------------------------------------------------------------------------------------
def setup_R():

    import os, sys, subprocess, importlib
    IN_ANACONDA = 'CONDA_DEFAULT_ENV' in os.environ      
    
    try:
        if subprocess.run(["R", "--version"], capture_output=True).returncode == 0:
            print("R installed")
    except FileNotFoundError:
        print("Installing R and essential packages (this can take a few minutes)")
        install_R()   

    if IN_ANACONDA:    

        # Set environment variables R_HOME and PATH for R in Python
        set_env_Win_macOS()
    
        # Check and install the Python package 'rpy2' from conda-forge
        python_package = 'rpy2'
        if importlib.util.find_spec(python_package) is None:
            # rpy2 is not installed, install it
            print(f"Installing {python_package}...")
            conda_channel = 'conda-forge'
            conda_command = ['conda', 'install', '--yes', '--prefix', sys.prefix, '-c', conda_channel, python_package]        
            subprocess.check_call(conda_command)
        #else:             
        #    print(f"{python_package} is already installed.") 

    return

#--------------------------------------------------------------------------------------------------
def initialize_rpy2():

    import os, platform, warnings

    # Determine the development tool
    IN_COLAB = 'COLAB_GPU' in os.environ  # True if running in Colab
    IN_ANACONDA = 'CONDA_DEFAULT_ENV' in os.environ  # True if running in Anaconda 

    # Determine the operating system (Windows, Darwin for macOS, or Linux)
    os_name = platform.system()
    print(f"Operating system: {os_name}")

    if IN_ANACONDA:
        # Set environment variables R_HOME and PATH for R in Python (to prevent JIT error for import rpy2.robjects)
        set_env_Win_macOS()
  
    # Enable Python-to-R object conversion
    import rpy2.robjects as ro
    from rpy2.robjects import pandas2ri
    pandas2ri.activate()
    from rpy2.robjects.vectors import StrVector   
 
    if IN_COLAB:   
        print("Development tool: Colab")           

        # Update R library path
        colab_lib_path = '/content/drive/MyDrive/Rlibs'           
        ro.r(f'.libPaths("{colab_lib_path}")') 
   
    if IN_ANACONDA:
    
        print("Development tool: Anaconda")       
        
        # The R bin directory needs to be added to PATH in R, then it loads dependencies R.dll, Rblas.dll and Rlapack.dll
        if os_name == 'Windows':             
            ro.r(r'''
                bin_path <- gsub("\\\\", "/", file.path(Sys.getenv("CONDA_PREFIX"), "Lib", "R", "bin", "x64"))
                Sys.setenv(PATH = paste(Sys.getenv("PATH"), bin_path, sep = ";"))
                bin_path2 <- gsub("\\\\", "/", file.path(Sys.getenv("CONDA_PREFIX"), "Lib", "R"))
                Sys.setenv(PATH = paste(Sys.getenv("PATH"), bin_path2, sep = ";"))
                ''')                       
        elif os_name == 'Darwin':
            ro.r('''
                Sys.setenv(PATH = paste(Sys.getenv("PATH"),
                    file.path(Sys.getenv("CONDA_PREFIX"), "lib", "R", "bin"), sep = ":"))
                ''')                    

        # Update R library path if needed
        #ro.r(r'''
        #    lib_path <- gsub("\\\\", "/", file.path(Sys.getenv("CONDA_PREFIX"), "Lib", "R", "library"))
        #    .libPaths(lib_path)
        #''')

    # Set an environment variable to suppress S3 method overwrite warning
    #s3 = ro.r(r'''
    #  do.call(Sys.setenv, list("_R_S3_METHOD_REGISTRATION_NOTE_OVERWRITES_" = "FALSE"))
    #''')
    
    # Suppress warning for %load_ext rpy2.ipython 
    warnings.filterwarnings("ignore", message=".*quartz.*", category=UserWarning)

    return ro, pandas2ri, StrVector

#--------------------------------------------------------------------------------------------------
def load_R_packages(R_pkgs_required):

    import os, subprocess, platform, logging
    import rpy2.robjects as ro
    from rpy2.rinterface_lib.callbacks import logger as rpy2_logger

    # Determine the development tool
    IN_COLAB = 'COLAB_GPU' in os.environ  # True if running in Colab
    IN_ANACONDA = 'CONDA_DEFAULT_ENV' in os.environ  # True if running in Anaconda 

    # Determine if any required R packages are not installed yet
    ro.globalenv['R_pkgs_required_list'] = R_pkgs_required
    ro.r('''       
        R_pkgs_required <- unlist(R_pkgs_required_list)
        R_pkgs_all <- rownames(installed.packages())
        R_pkgs_installed <- R_pkgs_required[R_pkgs_required %in% R_pkgs_all]   
        R_pkgs_missing <- setdiff(R_pkgs_required, R_pkgs_all)
    ''')
    R_pkgs_installed = ro.globalenv['R_pkgs_installed'].tolist() 
    #print('R packages already installed:', ", ".join(R_pkgs_installed)) if R_pkgs_installed else None 
    R_pkgs_missing = ro.globalenv['R_pkgs_missing'].tolist() 
    #print('R packages to be installed:', ", ".join(R_pkgs_missing)) if R_pkgs_missing else None 

    # Suppress R warnings for installation (restored below) 
    rpy2_logger.setLevel(logging.ERROR)
    ro.r('options(warn=-1)')  

    # R package installation of packages not installed yet
    if IN_COLAB:
        
        # Library path used only in Colab for saving R packages in Google Drive
        colab_lib_path = '/content/drive/MyDrive/Rlibs'
    
        # Create R library directory in Google Drive if it does not exist
        if not os.path.exists(colab_lib_path):
            os.makedirs(colab_lib_path)           
        
        # Update R library paths
        ro.r(f'.libPaths("{colab_lib_path}")')    
        
        # Install missing R packages 
        for pkg in R_pkgs_missing:

            print(f"Installing R package '{pkg}'...")

            # For these packages, install dependency libraries first (add packages to list if needed)
            if pkg in ['rmgarch']:
                prec_lib = True
            else:
                prec_lib = False

            if prec_lib:                
                subprocess.run(['sudo', 'apt-get', 'update'], check=True) # update apt information 
                # Install GNU Multiple Precision Arithmetic Library (GMP)
                print('Installing dependency libraries gmp and libgmp-dev')
                subprocess.run(['sudo', 'apt-get', 'install', '-y', 'libgmp-dev'], check=True) 
                # Install GNU Multiple Precision Floating-Point Reliable Library (MPFR)
                print('Installing dependency libraries mpfr and libmpfr-dev')
                subprocess.run(['sudo', 'apt-get', 'install', '-y', 'libmpfr-dev'], check=True)      

            # Package installation in Colab
            ro.r(f'suppressMessages(install.packages("{pkg}", lib="{colab_lib_path}", repos="http://cran.rstudio.com/"))')
            
    elif IN_ANACONDA:
              
        # Update Python and R library paths
        lib_path = os.path.join(os.environ['CONDA_PREFIX'], 'Lib', 'R', 'library')
        ro.r(r'''
            lib_path <- gsub("\\\\", "/", file.path(Sys.getenv("CONDA_PREFIX"), "Lib", "R", "library"))
            .libPaths(lib_path)
        ''')
            
        # Package installation in Anaconda                       
        for pkg in R_pkgs_missing:
            print(f"Installing R package '{pkg}'...")
            ro.r(f'suppressMessages(capture.output(install.packages("{pkg}", lib=lib_path, repos="http://cran.rstudio.com/")))');
            
        #cran_repo = "http://cran.rstudio.com/" ############################################################## DELETE IF NOT NEEDED
        #for pkg in R_pkgs_missing:
        #    print(f"Installing R package '{pkg}'...")        
        #    ro.r(f'install.packages("{pkg}", lib=lib_path, repos="{cran_repo}")')
                       
    else:
        print(f"In RPY.initialize_R_packages, unsupported Development tool")
      
    # Load required R packages
    ro.r(r'''
        suppressPackageStartupMessages(
        {sapply(R_pkgs_required, function(pkg) {library(pkg, character.only = TRUE, quietly = TRUE)})}
        )
    ''')

    # Verify loading
    ro.r('''       
        R_pkgs_loaded_all <- loadedNamespaces()
        R_pkgs_loaded <- R_pkgs_required[R_pkgs_required %in% R_pkgs_loaded_all]   
    ''')    
    R_pkgs_loaded = ro.globalenv['R_pkgs_loaded'].tolist() 
    print('R packages loaded:', ", ".join(R_pkgs_loaded)) 
   
    # Restore R warnings settings
    rpy2_logger.setLevel(logging.WARNING)
    ro.r('options(warn=0)')

    return 