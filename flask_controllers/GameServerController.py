# GameController is class based on Flask.MethodView which provides the logic
# required to handle get and post requests. It could also handle put, patch, etc.,
# but currently only supports GET (get a new game) and POST (make a guess against
# an existing game

# Import standard packages
import json
import socket
from redis.exceptions import ConnectionError

# Import flask packages
from flask import request, Response
from flask.views import MethodView
from flask_helpers.build_response import build_response
from werkzeug.exceptions import BadRequest

# Import the Game Controller
from Game.GameController import GameController

# Import the Flask app object
from python_cowbull_server import app, error_handler


class GameServerController(MethodView):
    """
    tbc
    """

    def __init__(self):
        """
        TBC
        """

        #
        # Get an error handler that can be used to handle errors and log to
        # std i/o. The error handler logs the error and forms an HTML response
        # using Flask's Response class.
        #
        self.handler = error_handler
        self.handler.module = "GameServerController"
        self.handler.method = "__init__"
        self.handler.log(message="Loading configuration from environment.", status=0)

        #
        # Get key configuration information from Flask's configuration engine.
        # These should have all been set before (in python_cowbull_server/__init__.py)
        # and if they haven't (for whatever reason) an exception WILL be raised.
        #
        self.game_version = app.config.get("GAME_VERSION")

        #
        # Persistence Engine selector, v2.0
        #
        self.persistence_engine = app.config.get("PERSISTER", None)
        if not self.persistence_engine:
            raise ValueError(
                "No persistence engine is defined and for some unknown "
                "reason, the default of redis did not make it through "
                "configuration!"
            )
        self.handler.log(message="Persistence engine set to: {}".format(self.persistence_engine.engine_name))

        #
        # Log the configuration to the handler.
        #
        self.handler.log(
            message="Persistence engine configured as "
                    "{} with parameters: {}".format(
                self.persistence_engine.engine_name,
                self.persistence_engine.parameters
            ),
            status=0
        )

    def get(self):
        """
        TBC
        :return:
        """

        #
        # Set the error handler to default the module and method so that logging
        # calls can be more precise and easier to read.
        #
        self.handler.method = "get"
        self.handler.log(message='Processing GET request', status=0)

        #
        # Check if a game mode has been passed as a query parameter. If it has,
        # use it to create the game. If it hasn't, then let the game decide.
        #
        self.handler.log(message='Fetching arguments (if any) passed to get')
        game_mode = request.args.get('mode', default=None, type=None)
        self.handler.log(message="game_mode value from request.args.get: {}, type: {}".format(game_mode, type(game_mode)))

        try:
            self.handler.log(message="Creating game with mode {} ({})".format(game_mode, type(game_mode)))
            game_controller = GameController(
                game_modes=app.config["COWBULL_CUSTOM_MODES"],
                mode=game_mode
            )
            self.handler.log(message='New game created with key {}'.format(game_controller.game.key), status=0)
        except ValueError as ve:
            return self.handler.error(
                status=400,
                exception="Invalid game mode",
                message="{}: game mode {}!".format(str(ve), game_mode)
            )

        # Get a persistence engine. The persister is set in configuration
        # and dynamically loaded at the start of the transaction. See
        # Persistence/PersistenceEngine.py for more info.
        self.handler.log(message="Fetching persistence engine - {}".format(self.persistence_engine.engine_name))
        persister = self.persistence_engine.persister
        self.handler.log(message='Persister instantiated', status=0)

        #
        # Save the newly created game to the persistence engine
        #
        self.handler.log(message="Saving game to persister")
        persister.save(game_controller.game.key, game_controller.save())
        self.handler.log(message='Game {} persisted.'.format(game_controller.game.key), status=0)

        #
        # Build the user response - key, no. of digits, and no. of guesses
        #
        _response = {
            "key": game_controller.game.key,
            "mode": game_controller.game.mode.mode,
            "digits": game_controller.game.mode.digits,
            "digit-type": game_controller.game.mode.digit_type,
            "guesses": game_controller.game.mode.guesses_allowed,
            "served-by": socket.gethostname(),
            "help-text": game_controller.game.mode.help_text,
            "instruction-text": game_controller.game.mode.instruction_text
        }

        self.handler.log(message='GET request fulfilled. Returned: {}'.format(_response), status=0)

        return build_response(
            html_status=200,
            response_data=_response,
            response_mimetype="application/json"
        )

    def post(self):
        """
        TBC
        :return:
        """

        self.handler.method = "post"
        self.handler.log(message='Processing POST request.', status=0)

        json_dict = self._fetch_json(request=request)

        #
        # Get a persister to enable the game to be loaded and then saved (updated).
        # See the GET method above for more information on the persister.
        #
        self.handler.log(message='Getting persister', status=0)
        persister = self.persistence_engine.persister

        _key = self._get_key(json_dict=json_dict)
        if not isinstance(_key, str):
            return _key

        self.handler.log(message='Attempting to execute_load game {}'.format(_key), status=0)
        _loaded_game = self._load_game(key=_key, persister=persister)
        if not isinstance(_loaded_game, dict):
            return _loaded_game

        _game = self._get_game(
            _loaded_game,
            app
        )
        self.handler.log(message='Loaded game {}'.format(_key), status=0)


        self.handler.log(message='Getting digits from {}'.format(json_dict))
        _guesses = self._get_digits(json_dict=json_dict)
        if isinstance(_guesses, Response):
            return _guesses
        self.handler.log(message='Guesses extracted from JSON: {}'.format(_guesses), status=0)

        self.handler.log(message="In guess")
        self.handler.log(message='Making a guess with digits: {}'.format(_guesses), status=0)

        #
        # Make a guess
        #
        try:
            _analysis = _game.guess(*_guesses)
        except ValueError as ve:
            return self.handler.error(
                status=400,
                exception=str(ve),
                message="There is a problem with the digits provided!"
            )
        self.handler.log(message='Retrieved guess analysis', status=0)

        #
        # Save the game
        #
        self.handler.log(message="Saving game to persister")
        save_game = _game.save()
        persister.save(key=_key, jsonstr=save_game)
        self.handler.log(message='Game {} persisted.'.format(_key), status=0)

        #
        # Return the analysis of the guess to the user.
        #
        _display_info = json.loads(save_game)
        del(_display_info["answer"])
        _return_response = \
            {
                "game": _display_info,
                "outcome": _analysis,
                "served-by": socket.gethostname()
            }

        self.handler.log(message='Returning analysis and game info to caller', status=0)
        return build_response(response_data=_return_response)

    # Private methods
    def _fetch_json(self, request=None):
        #
        # Get the JSON from the POST request. If there is no JSON then an exception
        # is raised. IMPORTANT NOTE: When debugging ensuring the Content-type is
        # set to application/json - for example (using cURL):
        #
        # curl -H "Content-type: application/json" ...
        #
        try:
            self.handler.log(message='Attempting to execute_load JSON', status=0)
            json_dict = request.get_json()
            self.handler.log(message='Loaded JSON. Returned: {}'.format(json_dict), status=0)
        except BadRequest as e:
            return self.handler.error(
                status=400,
                exception=e.description,
                message="Bad request. There was no JSON present. Are you sure the "
                        "header Content-type is set to application/json?"
            )
        return json_dict

    def _get_key(self, json_dict=None):
        #
        # Get the game key from the JSON provided above. If it does not exist,
        # return a 400 status (client) error
        #
        key = None
        try:
            key = json_dict["key"]
            if not key:
                raise KeyError("Key is null")
            if not isinstance(key, str):
                raise KeyError("Key is not a string!")
        except TypeError as te:
            return self.handler.error(
                status=400,
                exception=str(te),
                message="Bad request. For some reason the json_dict is None! Are you "
                        "sure the header is set to application/json?"
            )
        except KeyError as ke:
            return self.handler.error(
                status=400,
                exception=str(ke),
                message="Bad request. For some reason the json_dict does not contain "
                        "a key! Are you sure the header is set to application/json and "
                        "a key is present?"
            )
        return key

    def _load_game(self, key=None, persister=None):
        #
        # Load the game based on the key contained in the JSON provided to
        # the POST request. If the JSON data is invalid, return a
        # response to the user indicating an HTML status, the exception, and an
        # explanatory message. If the data
        #
        _persisted_response = None
        try:
            _persisted_response = persister.load(key=key)
        except KeyError as ke:
            return self.handler.error(
                status=400,
                exception=str(ke),
                message="The request must contain a valid game key."
            )

        try:
            _loaded_game = json.loads(_persisted_response)
        except Exception as e:
            return self.handler.error(
                status=400,
                exception=str(e),
                message="Exception while trying to load game from game key."
            )
        return _loaded_game

    def _get_game(
        self,
        loaded_game,
        app
    ):
        #
        # Load the game based on the key contained in the JSON provided to
        # the POST request. If the JSON data is invalid, return a
        # response to the user indicating an HTML status, the exception, and an
        # explanatory message. If the data
        #
        self.handler.log(message="Loading game mode from: {}.".format(loaded_game["mode"]))
        _mode = loaded_game["mode"]
        self.handler.log(message="Loaded game mode {}.".format(str(_mode["mode"])))

        _game = GameController(
            game_modes=app.config["COWBULL_CUSTOM_MODES"],
            game_json=json.dumps(loaded_game),
            mode=str(_mode["mode"])
        )
        return _game

    def _get_digits(self, json_dict=None):
        #
        # Get the digits being guessed and add them to a list
        #
        try:
            _guesses = json_dict["digits"]
        except KeyError as ke:
            return self.handler.error(
                status=400,
                exception=str(ke),
                message="The request must contain an array of digits called 'digits'"
            )
        return _guesses

