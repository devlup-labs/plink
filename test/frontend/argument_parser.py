import unittest
from unittest.mock import patch
import sys

# Test for parsing_argument from argument_parser.py
from argument_parser import parsing_argument

class TestArgumentParser(unittest.TestCase):

    def test_send_basic(self):
        test_args = ['prog', 'send', 'file.txt']
        with patch.object(sys, 'argv', test_args):
            args = parsing_argument()
            self.assertEqual(args.command, 'send')
            self.assertEqual(args.filepath, 'file.txt')
            self.assertEqual(args.port, 8080)
            self.assertFalse(args.compress)

    def test_send_all_options(self):
        test_args = ['prog', 'send', 'data.txt', '-m', 'direct', '-p', '9090', '-e', 'aes256',
                     '-c', '512', '--compress', '--password', 'secret123', '--timeout', '30',
                     '--resume', '--verify']
        with patch.object(sys, 'argv', test_args):
            args = parsing_argument()
            self.assertEqual(args.method, 'direct')
            self.assertEqual(args.port, 9090)
            self.assertTrue(args.compress)
            self.assertTrue(args.resume)
            self.assertTrue(args.verify)

    def test_receive_basic(self):
        test_args = ['prog', 'receive']
        with patch.object(sys, 'argv', test_args):
            args = parsing_argument()
            self.assertEqual(args.command, 'receive')
            self.assertEqual(args.output_dir, '.')
            self.assertEqual(args.port, 8080)

    def test_receive_with_options(self):
        test_args = ['prog', 'receive', '-o', 'downloads', '--port', '9999',
                     '--method', 'upnp', '--password', 'secret', '--auto-accept',
                     '--max-size', '100']
        with patch.object(sys, 'argv', test_args):
            args = parsing_argument()
            self.assertEqual(args.output_dir, 'downloads')
            self.assertEqual(args.port, 9999)
            self.assertTrue(args.auto_accept)
            self.assertEqual(args.max_size, 100)
