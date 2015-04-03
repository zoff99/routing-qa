git clone https://github.com/navit-gps/navit.git
pushd
git checkout $CIRCLE_BRANCH
popd
mkdir bin
cmake ../ -Dgraphics/qt_qpainter:BOOL=FALSE -Dgui/qml:BOOL=FALSE -DSAMPLE_MAP:BOOL=FALSE
make -j32
