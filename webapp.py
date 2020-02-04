from flask import Flask
from server import blueprint
from effectrunner import EffectRunner
from effects import airdraw


def create_app(config_file):
    app = Flask(__name__)  # Create application object
    app.config.from_pyfile(config_file)  # Configure application with settings file, not strictly necessary
    app.config['test']='test'

    effect_runner = EffectRunner()
    effect_runner.startEffect(airdraw.AirDraw())
    #effect_runner.setEffect(airdraw.AirDraw())
    #effect_runner.start()
    app.register_blueprint(blueprint.construct_blueprint(effect_runner))  # Register url's so application knows what to do
    return app

if __name__ == '__main__':
    app = create_app('settingslocal.py')  # Create application with our config file
    app.run(use_reloader=False, debug=True)  # Run our application
