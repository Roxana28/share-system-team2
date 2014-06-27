__author__ = 'milly'

import unittest
import os
import shutil
import json

import httpretty
import client_daemon


TEST_DIR = 'daemon_test'
LAST_TIMESTAMP = 'last_timestamp'
GLOBAL_MD5 = 'global_md5'

server_timestamp = 1
files = {'ciao.txt': (3, 'md5md6'),
         'carlo.txt': (2, 'md6md6')}

base_dir_tree = {
    # <filepath>: (<timestamp>, <md5>)
    'ciao.txt':         (3, 'md5md6'),
    'carlo.txt':        (2, 'md6md6'),
    './Pytt/diaco.txt': (12, '7645jghkjhdfk'),
    'pasquale.cat':     (12, 'khgraiuy8qu4l'),
    'carlo.buo':        (14, 'rfhglkr94094580'),
}


def folder_modified():
    """
    Return True to indicate that sharing folder is modified during daemon is down
    """
    return True

start_dir = os.getcwd()


def setup_test_dir():
    """
    Create (if needed) <TEST_DIR> directory starting from current directory and change current directory to the new one.
    """
    try:
        os.mkdir(TEST_DIR)
    except OSError:
        pass

    os.chdir(TEST_DIR)


def tear_down_test_dir():
    """
    Return to initial directory and remove the <TEST_DIR> one.
    """
    os.chdir(start_dir)
    shutil.rmtree(TEST_DIR)


def create_file(file_path, content=''):
    print 'Creating "{}"'.format(file_path)
    dirname = os.path.dirname(file_path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    assert os.path.isdir(dirname), '{} must be a directory'.format(dirname)

    with open(file_path, 'w') as fp:
        fp.write(content)
    return os.path.getmtime(file_path)


class FileFakeEvent(object):
    """
    Class that simulates a file related event sent from watchdog.
    Actually create 'src_path' attribute and the file in disk.
    """
    def __init__(self, src_path, content=''):
        self.src_path = src_path
        create_file(self.src_path, content=content)


class TestClientDaemon(unittest.TestCase):
    def setUp(self):
        self.client_daemon = client_daemon.Daemon()

    def test_sync_process_directory_not_modified1(self):
        """
        Test the case: (it must do nothing)
        Directory not modified,
        timestamp client == timestamp server
        """
        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': server_timestamp}
        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()
        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            []
        )

    def test_sync_process_directory_not_modified2(self):
        """
        Test the case: (it must download the file)
        Directory not modified,
        timestamp client < timestamp server
        new file on server and not in client
        """
        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': 17}

        files = base_dir_tree.copy()
        files.update({'new': (18, 'md5md6jkshkfv')})
        self.client_daemon.client_snapshot = base_dir_tree.copy()

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            [('download', 'new'), ]
        )

    def test_sync_process_directory_not_modified3(self):
        """
        Test the case: (it must copy or rename the file)
        Directory not modified,
        timestamp client < timestamp server
        new file on server and in client but with different filepath
        """
        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': 17}

        files = base_dir_tree.copy()
        files.update({'new': (18, 'md5md6')})
        self.client_daemon.client_snapshot = base_dir_tree.copy()

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            []
        )

    def test_sync_process_directory_not_modified4(self):
        """
        Test the case: (it must download the file)
        Directory not modified,
        timestamp client < timestamp server
        file modified on server
        """
        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': 17}

        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()
        files['carlo.txt'] = (server_timestamp, 'md5 diverso')

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            [('download', 'carlo.txt'), ]
        )

    def test_sync_process_directory_not_modified5(self):
        """
        Test the case: (it must delete the file on client)
        Directory not modified,
        timestamp client < timestamp server
        file is missing on server
        """
        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': 17}

        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()
        self.client_daemon.client_snapshot.update({'carlito.txt': (1, 'jkdhlghkg')})

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            []
        )

    def test_sync_process_directory_modified1(self):
        """
        Test the case: (it must do nothing)
        Directory modified,
        timestamp client == timestamp server
        client is already synchronized with server
        """
        self.client_daemon._is_directory_modified = folder_modified

        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': server_timestamp}

        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            []
        )

    def test_sync_process_directory_modified2(self):
        """
        Test the case: (it must delete the file on server)
        Directory modified,
        timestamp client == timestamp server
        new file on server and not on client
        """
        self.client_daemon._is_directory_modified = folder_modified

        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': server_timestamp}

        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()
        files.update({'new': (18, 'md5md6jkshkfv')})

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            [('delete', 'new')]
        )

    def test_sync_process_directory_modified3(self):
        """
        Test the case: (it must modify the file on server)
        Directory modified,
        timestamp client == timestamp server
        file modified
        """
        self.client_daemon._is_directory_modified = folder_modified

        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': server_timestamp}

        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()
        files['carlo.txt'] = (server_timestamp, 'md5 diverso')

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            [('modified', 'carlo.txt')]
        )

    def test_sync_process_directory_modified4(self):
        """
        Test the case: (it must upload the file on server)
        Directory modified,
        timestamp client == timestamp server
        new file in client and not on server
        """
        self.client_daemon._is_directory_modified = folder_modified

        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': server_timestamp}

        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()
        files.pop('carlo.txt')

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            [('upload', 'carlo.txt')]
        )

    def test_sync_process_directory_modified5(self):
        """
        Test the case: (it must download the file)
        Directory modified,
        timestamp client < timestamp server
        new file on server and not in client
        file timestamp > client timestamp
        """
        self.client_daemon._is_directory_modified = folder_modified

        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': 17}

        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()
        files.update({'new': (18, 'md5md6jkshkfv')})

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            [('download', 'new')]
        )

    def test_sync_process_directory_modified6(self):
        """
        Test the case: (it must delete the file)
        Directory modified,
        timestamp client < timestamp server
        new file on server and not in client
        file timestamp < client timestamp
        """
        self.client_daemon._is_directory_modified = folder_modified

        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': 17}

        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()
        files.update({'new': (16, 'md5md6jkshkfv')})

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            [('delete', 'new')]
        )

    def test_sync_process_directory_modified7(self):
        """
        Test the case: (it must copy or move the file)
        Directory modified,
        timestamp client < timestamp server
        new file on server and in client
        """
        self.client_daemon._is_directory_modified = folder_modified

        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': 17}

        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()
        files.update({'new': (16, 'md5md6')})

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            []
        )

    def test_sync_process_directory_modified8(self):
        """
        Test the case: (it must modify the file on server)
        Directory modified,
        timestamp client < timestamp server
        file modified
        file timestamp < client timestamp
        """
        self.client_daemon._is_directory_modified = folder_modified

        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': 17}

        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()
        files['carlo.txt'] = (16, 'md5md6jkshkfv')

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            [('modify', 'carlo.txt')]
        )

    def test_sync_process_directory_modified9(self):
        """
        Test the case: (there is a conflict, so it upload the file on server with ".conflicted" extension)
        Directory modified,
        timestamp client < timestamp server
        file modified
        file timestamp > client timestamp
        """
        self.client_daemon._is_directory_modified = folder_modified

        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': 17}

        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()
        files['carlo.txt'] = (18, 'md5md6jkshkfv')

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            [('upload', ''.join(['carlo.txt', '.conflicted']))]
        )

    def test_sync_process_directory_modified10(self):
        """
        Test the case: (it upload the file on server)
        Directory modified,
        timestamp client < timestamp server
        new file in client and not on server
        """
        self.client_daemon._is_directory_modified = folder_modified

        server_timestamp = 18
        self.client_daemon.local_dir_state = {'last_timestamp': 17}

        files = base_dir_tree.copy()
        self.client_daemon.client_snapshot = base_dir_tree.copy()
        files.pop('carlo.txt')

        self.assertEqual(
            self.client_daemon._sync_process(server_timestamp, files),
            [('upload', 'carlo.txt')]
        )


class TestClientDaemonOnEvents(unittest.TestCase):
    CONFIG_DIR = os.path.join(os.environ['HOME'], '.PyBox')
    CONFIG_FILEPATH = os.path.join(CONFIG_DIR, 'daemon_config')
    LOCAL_DIR_STATE_PATH = os.path.join(CONFIG_DIR, 'dir_state')

    def setUp(self):
        setup_test_dir()
        httpretty.enable()

        #self.cm = ConnectionManager()
        with open(self.CONFIG_FILEPATH) as fo:
            self.cfg = json.load(fo)

        self.auth = self.cfg['user'], self.cfg['pass']
        self.cfg['server_address'] = "http://localhost:5000"

        # create this auth testing
        self.authServerAddress = "http://" + self.cfg['user'] + ":" + self.cfg['pass']
        self.base_url = self.cfg['server_address'] + self.cfg['api_suffix']
        self.files_url = self.base_url + 'files/'

        # Instantiate the daemon
        self.client_daemon = client_daemon.Daemon()

        # Injecting a fake client snapshot
        md5 = '50abe822532a06fb733ea3bc089527af'
        ts = 1403878699

        self.client_daemon.client_snapshot = {'dir/file.txt': [ts, md5]}
        self.client_daemon.local_dir_state = {LAST_TIMESTAMP: ts, GLOBAL_MD5: md5}

    def tearDown(self):
        httpretty.disable()
        httpretty.reset()
        tear_down_test_dir()

    @httpretty.activate
    def test_on_created(self):
        """
        Test on_created method of daemon when a new file is created.
        """
        start_state = self.client_daemon.local_dir_state.copy()
        ts1 = start_state[LAST_TIMESTAMP]
        ts2 = ts1 + 60  # arbitrary value

        # new file I'm going to create in client sharing folder
        new_path = 'created_file.txt'

        url = self.files_url + new_path
        httpretty.register_uri(httpretty.POST, url, status=201,
                               body='{"server_timestamp":%d}' % ts2,
                               content_type="application/json")

        abs_path = os.path.join(self.client_daemon.cfg['sharing_path'], new_path)
        event = FileFakeEvent(abs_path)

        self.client_daemon.on_created(event)
        # test that the new path is in the client_snapshot
        self.assertIn(new_path, self.client_daemon.client_snapshot)
        # simply check that local_dir_state is changed
        self.assertNotEqual(start_state, self.client_daemon.local_dir_state)

        # # daemon.local_dir_state should be a dict
        self.assertIsInstance(self.client_daemon.local_dir_state, dict)
        # last_timestamp should be an int
        self.assertIsInstance(self.client_daemon.local_dir_state[LAST_TIMESTAMP], int)
        # test exact value of timestamp
        self.assertEqual(self.client_daemon.local_dir_state[LAST_TIMESTAMP], ts2)


if __name__ == '__main__':
    unittest.main(verbosity=3)
            