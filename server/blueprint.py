from flask import Blueprint

def construct_blueprint(effect_runner):
    home_view = Blueprint('home_view', __name__)

    @home_view.route('/')  # Route for the page
    @home_view.route('/status')
    def display_status():
        print("getting status")
        out = 'Effect Runner is '
        if not effect_runner.effect or not effect_runner.effect.running:
            out = out + 'not '
        out = out + 'running! At Tick: '
        out = out + str(effect_runner.effect.tick_count)
        out = out + '<br />'
        out = out + effect_runner.effect.getStatus()
        return out

    @home_view.route('/start')
    def start():
        return #deprecated
        if effect_runner is not None:
            effect_runner.stopEffect()
            #effect_runner.join()

        effect_runner.startEffect()
        out = 'Restarting'
        return out

    @home_view.route('/stop')
    def stop():
        effect_runner.stopEffect()
        out = 'Stopping'
        return out

    return home_view
