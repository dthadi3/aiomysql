import time

import aiomysql
from tests._testutils import run_until_complete
from tests.base import AIOPyMySQLTestCase


class TestConnection(AIOPyMySQLTestCase):

    @run_until_complete
    def test_utf8mb4(self):
        """This test requires MySQL >= 5.5"""
        arg = self.databases[0].copy()
        arg['charset'] = 'utf8mb4'
        conn = yield from aiomysql.connect(loop=self.loop, **arg)

    @run_until_complete
    def test_largedata(self):
        """Large query and response (>=16MB)"""
        cur = self.connections[0].cursor()
        yield from cur.execute("SELECT @@max_allowed_packet")
        if cur.fetchone()[0] < 16*1024*1024 + 10:
            print("Set max_allowed_packet to bigger than 17MB")
        else:
            t = 'a' * (16*1024*1024)
            yield from cur.execute("SELECT '" + t + "'")
            assert cur.fetchone()[0] == t

    @run_until_complete
    def test_escape_string(self):
        con = self.connections[0]
        cur = con.cursor()

        self.assertEqual(con.escape("foo'bar"), "'foo\\'bar'")
        yield from cur.execute("SET sql_mode='NO_BACKSLASH_ESCAPES'")
        self.assertEqual(con.escape("foo'bar"), "'foo''bar'")

    @run_until_complete
    def test_autocommit(self):
        con = self.connections[0]
        self.assertFalse(con.get_autocommit())

        cur = con.cursor()
        yield from cur.execute("SET AUTOCOMMIT=1")
        self.assertTrue(con.get_autocommit())

        yield from con.autocommit(False)
        self.assertFalse(con.get_autocommit())
        yield from cur.execute("SELECT @@AUTOCOMMIT")
        self.assertEqual(cur.fetchone()[0], 0)

    @run_until_complete
    def test_select_db(self):
        con = self.connections[0]
        current_db = self.databases[0]['db']
        other_db = self.databases[1]['db']

        cur = con.cursor()
        yield from cur.execute('SELECT database()')
        self.assertEqual(cur.fetchone()[0], current_db)

        yield from con.select_db(other_db)
        yield from cur.execute('SELECT database()')
        self.assertEqual(cur.fetchone()[0], other_db)

    @run_until_complete
    def test_connection_gone_away(self):
        """
        http://dev.mysql.com/doc/refman/5.0/en/gone-away.html
        http://dev.mysql.com/doc/refman/5.0/en/error-messages-client.html#error_cr_server_gone_error
        """
        con = self.connections[0]
        cur = con.cursor()
        yield from cur.execute("SET wait_timeout=1")
        time.sleep(2)
        with self.assertRaises(aiomysql.OperationalError) as cm:
            yield from cur.execute("SELECT 1+1")
        # error occures while reading, not writing because of socket buffer.
        #self.assertEquals(cm.exception.args[0], 2006)
        self.assertIn(cm.exception.args[0], (2006, 2013))

