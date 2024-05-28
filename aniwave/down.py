from constants import flask_app

@flask_app.route("/thanksForTheServerRessources", methods=["POST"])
def get_video_url():
    return "This endpoint has been retired. Please dm @Nixuge on telegram/discord/anything found on https://nixuge.me for an alternative.", 503
