"""Test the msgboard API.

"""

import os
import json
import base64
import unittest
import tempfile
import functools

from ..msgboard import msg


class MsgboardTestCase(unittest.TestCase):

    # TODO: docstring
    def setUp(self):
        self.db_fd, msg.app.config['DATABASE'] = tempfile.mkstemp()
        msg.app.config['TESTING'] = True
        self.app = msg.app.test_client()
        msg.init_db()

    # TODO: docstring
    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(msg.app.config['DATABASE'])

    def test_empty_db(self):
        """If the database is empty, a GET request
        to /message endpoint should return a blank list.

        """

        message_range = {"offset": 0, "limit": 10}
        response = self.get('/messages', data=message_range)
        assert [] == response

    def __getattr__(self, attribute_name):
        """This is so you can call self.post, self.get, self.put,
        self.post, etc. This only happens when there is no such
        attribute of name...

        Note:
            If you don't know, __getattr__ is only activated
            when a property is accessed (attribute_name), yet
            doesn't actually exist.

        Arguments:
            attribute_name (str): One of: post, get, put, or delete.

        Raises:
            AttributeError: if attribute_name is not one of post, get,
                put, or delete.

        Returns:
            partial: returns the self.call method, except with the
                first argument, the request type, already filled out
                depending on the attribute_name, e.g., post, get.

        """

        if attribute_name.lower() in ('post', 'get', 'put', 'delete'):
            specific_call_method = functools.partial(self.call,
                                                     attribute_name.lower())
            return specific_call_method

        raise AttributeError("%s is not valid method" % attribute_name)

    @staticmethod
    def make_base64_header(username, password):
        """Create Authorization header dict, for HTTPBasicAuth.

        Arguments:
            username (str):
            password (str):

        Returns:
            dict: Typical HTTPBasicAuth header for authorization.

        """

        cred_string = ("%s:%s" % (username, password)).encode('utf-8')
        base64_creds = base64.b64encode(cred_string)
        headers = {'Authorization': 'Basic '.encode('utf-8') + base64_creds}
        return headers

    # TODO: doc *args and **kwargs
    def call(self, method, *args, **kwargs):
        """Because we're tired of entering content_type and
        translating JSON constantly!

        Arguments:
            method (str): a valid request method, e.g., post.
            *args: --
            **kwargs: --

        """

        method = method.lower()
        kwargs['content_type'] = 'application/json'

        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])

        response = getattr(self.app, method)(*args, **kwargs)
        return json.loads(response.get_data(as_text=True))

    def test_create_user(self):
        """Create a user by POST'ing the correct
        JSON data to the /user endpoint.

        """

        # Create and send the user data
        user_data = {
                     "username": 'testuser',
                     "password": 'testpass'
                    }

        response = self.post('/user', data=user_data)

        # parse the JSON response and remove the created
        # datetime because that's not predictable
        del response["created"]
        # We expect the response will be this.
        user_fixture = {
                        "username": "testuser",
                        "id": 1,
                        "bio": None
                       }
        # test the expected response vs. actual
        assert user_fixture == response

    def test_create_existing_user(self):
        """Attempt to created a user that is already
        in the database.

        """

        self.test_create_user()

        user_data = {
                     "username": 'testuser',
                     "password": 'testpass'
                    }

        message = "A user already exists with username: testuser"

        response_fixture = {
                            "message": message
                           }

        response = self.post('/user', data=user_data)

        assert response_fixture == response

    def test_get_user(self):
        """Prove we can get a user by user ID
        *or* username.

        """

        a user and then get that users 
        self.test_create_user()
        user_fixture = {
                        "username": 'testuser',
                        "id": 1,
                        "bio": None
                       }
        # First test by using the user_id
        id_response = self.get('/user/1')
        del id_response["created"]
        assert user_fixture == id_response

        # Then test by using the username
        name_response = self.get('/user/testuser')
        del name_response["created"]

        assert user_fixture == name_response

    def test_get_wrong_user(self):
        """Verify the behavior for making
        various erroneous calls to get user.

        """

        self.test_create_user()
        no_info_fixture = {
                           "message": "Must specify user_id or username."
                          }
        no_id_fixture = {
                         "message": "No user matching ID: 69"
                        }
        no_name_fixture = {
                           "message": "No user matching username: notauser"
                          }

        no_info_response = self.get('/user')
        assert no_info_response == no_info_fixture

        id_response = self.get('/user/69')
        assert id_response == no_id_fixture

        name_response = self.get('/user/notauser')
        assert name_response == no_name_fixture

    def test_post(self):
        """Test creating a message.

        """

        self.test_create_user()

        message_content = {"text": 'I am a message.'}
        headers = self.make_base64_header("testuser", "testpass")
        response = self.post('/message', headers=headers, data=message_content)

        del response["created"]
        del response["user"]["created"]

        post_fixture = {
                        "id": 1,
                        "text": 'I am a message.',
                        "user": {
                                 "bio": None,
                                 "id": 1,
                                 "username": 'testuser'
                                }
                       }

        # you're getting NONE here because the user isn't created
        assert post_fixture == response

    def test_get_post(self):
        self.test_post()
        response = self.get('/message/1')
        del response['created']
        del response['user']['created']

        post_fixture = {
                        "id": 1,
                        "text": 'I am a message.',
                        "user": {
                                 "bio": None,
                                 "id": 1,
                                 "username": 'testuser'
                                }
                       }
        assert post_fixture == response

    def test_edit_message(self):
        """Test that a user can edit their own message

        """

        self.test_get_post()
        edited_post_fixture = {
                               "id": 1,
                               "text": 'I am an edited message.',
                               "user": {
                                        "bio": None,
                                        "id": 1,
                                        "username": 'testuser'
                                       }
                              }
        edit_content = {"text": 'I am an edited message.'}
        headers = self.make_base64_header("testuser", "testpass")
        response = self.put('/message/1', headers=headers, data=edit_content)

        del response["created"]
        del response["user"]["created"]

        assert edited_post_fixture == response

    def test_edit_post_bad_auth(self):
        """Test that unauthorized users cannot edit
        posts.

        """

        # Create fixtures
        wrong_user_fixture = {
                              "message": "You are not this message's author."
                             }
        no_login_fixture = None
        nonexistent_user_fixture = None
        edit_content = {
                        "text": "Can't edit these nuts."
                       }
        data = edit_content

        # Create user and post
        self.test_get_post()

        # Create a second user
        second_user = {
                       "username": 'testuser2',
                       "password": 'testpass'
                      }
        self.app.post('/user', data=json.dumps(second_user),
                      content_type='application/json')

        # Try to edit first user's post
        headers = self.make_base64_header("testuser2", "testpass")
        response = self.put('/message/1', headers=headers, data=data,
                            content_type='application/json')

        assert wrong_user_fixture == response


if __name__ == '__main__':
    unittest.main()
