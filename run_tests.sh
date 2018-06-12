export RENDER_EXAMPLE_DATA=/tmp
export RENDER_CLIENT_JAR=`greadlink -m ../render/render-ws-java-client/target/render-ws-java-client-2.0.1-SNAPSHOT-standalone.jar`
export RENDER_CLIENT_SCRIPTS=`greadlink -m ../render/render-ws-java-client/src/main/scripts/`
export RENDER_HOST=localhost
export RENDER_JAVA_HOME=`/usr/libexec/java_home -v 1.8`
cp -R ~/RenderStack/render/render-ws-java-client/src/main/resources/example_1 /tmp/.
cp -R ~/RenderStack/render/render-app/src/test/resources/multichannel-test/ /tmp/multichannel-test/.
docker-compose up -d
python setup.py test -a integration_tests/test_stack_integrated.py
docker-compose down