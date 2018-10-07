# Get darknet-nnpack and NNPack-darknet

Sources

* https://github.com/digitalbrain79/darknet-nnpack
* https://github.com/digitalbrain79/NNPACK-darknet
  * When running ninja and make on RPi3, add `-j 3` parameter to prevent system from being blocked.


# Link NNPack and pthreadpool libraries

Because NNPACK-darknet only generates static libraries (.a).

1. Modify build.ninja and add -fPIC (and -shared?) to cflags, still only create .a. 
  1. But it's okay because the key is `-fPIC`. Compiler can combine
     static libraries and object files if static libraries contain
     PIC object files.
1. [Patch](https://github.com/DT42/darknet-nnpack/blob/debian/debian/patches/01-use-nnpack-rpi3.patch) darknet-nnpack source and Makefile.
  * I patched C code directly because the Darknet library users will have consistent API, and do not need to initialize NNPack and pthreadpool by themselves.
  * You can initialize NNPack and pthreadpool in Python ([example](https://github.com/NTUEE-ESLab/2017Fall-IntelligentSecurityGuard/blob/master/replace/darknet.py#L110) to initialize NNPack only).
  * Simpler than adding `-Wl,--whole-archive /usr/lib/libnnpack.a /usr/lib/libpthreadpool.a -Wl,--no-whole-archive`
     to darknet-nnpack Makefile in NNPACK section.

References

* Issue discussion
  * https://github.com/digitalbrain79/darknet-nnpack/issues/17
  * https://github.com/Maratyszcza/NNPACK/issues/70
* Link .a to .so
  * https://stackoverflow.com/questions/2649735/how-to-link-static-library-into-dynamic-library-in-gcc
  * ftp://ftp.gnu.org/old-gnu/Manuals/ld-2.9.1/html_node/ld_3.html


# Verification

Run [darknet_npinput_rpi.py](https://github.com/DT42/darknet-numpy/blob/master/darknet_npinput_rpi.py) which loads libdarknet and model from system filepaths.


# Further Optimization

Sources

* https://github.com/shizukachan/darknet-nnpack
* https://github.com/shizukachan/NNPACK
  * Known issues: https://gitlab.com/bafu/nnpack-bin/issues/1


# Upstream NNPACK (drop)

Steps

1. $ pip3 install --user --upgrade confu  # update from v0.0.1 to v0.0.3, use pip3 instead of pip
1. $ sudo apt install clog
