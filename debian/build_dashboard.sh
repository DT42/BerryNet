#!/bin/bash

dashboard_version="8f24074"
if [ ! -e "dashboard" ]; then
    git clone https://github.com/v-i-s-h/PiIoT-dashboard.git dashboard
    pushd dashboard > /dev/null
    git reset --hard $dashboard_version
    find -name '*.ttf' -exec chmod a-x {} \;
    find -name '*.html' -exec chmod a-x {} \;
    find -name '*.woff' -exec chmod a-x {} \;
    find -name '*.json' -exec chmod a-x {} \;
    find -name '*.css' -exec chmod a-x {} \;
    find -name '*.eot' -exec chmod a-x {} \;
    find -name '*.md' -exec chmod a-x {} \;
    find -name 'LICENSE' -exec chmod a-x {} \;
    patch -p 1 < ../patch/ui-dt42-theme.patch
    cp ../patch/www/freeboard/img/dt42-logo.png www/freeboard/img
    cp ../patch/www/freeboard/css/dt42.css www/freeboard/css
    cp ../config/dashboard.json www/freeboard/
    sed -i 's/mime.lookup/mime.getType/' server.js
    rm -rf .git
    find -name '.gitignore' -exec rm -f {} \;
    popd > /dev/null
fi

