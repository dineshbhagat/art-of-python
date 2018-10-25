""" Demonstrating psycopg2 transactions

Reference: https://bbengfort.github.io/observations/2017/12/06/psycopg2-transactions.html
"""

import os
import json
import psycopg2 as pg


def connect_to_db(configpath):
    """
    Connect to PostgreSQL and return connection
    """
    with open(configpath, 'r') as f:
        config = json.load(f)
        # read keys from json config
        DB_NAME = config['db']
        USER = config['user']
        PASSWORD = config['password']
        # return connection string
        return pg.connect('dbname={0} user={1} password={2}'.format(DB_NAME, USER, PASSWORD))


def create_schema(conn, schemapath):
    """
    DROP/ CREATE schema from file
    """
    with open(schemapath, 'r') as f:
        sql = f.read()
    try:
        with conn.cursor() as curs:
            curs.execute(sql)
            conn.commit()
    except Exception as e:
        print('Schema creation error, rollback!')
        conn.rollback()
        raise e


def dogfeed(conn, feedpath):
    """
    Inserts seed data to users and accounts table
    """
    with open(feedpath, 'r') as f:
        sql = f.read()
    try:
        with conn.cursor() as curs:
            curs.execute(sql)
        conn.commit()
    except Exception as e:
        print('Dogfeed error, rollback!')
        conn.rollback()
        raise e


def make_deposit(conn, userid, acctype, amount):
    """
    Makes deposit to the account
    """
    print('\n\nUpdating account user:{}, type:{}, amount:{}'.format(userid, acctype, amount))
    with conn.cursor() as curs:
        try:
            res = curs.execute("""UPDATE accounts
                                    SET balance=%s
                                    WHERE owner_id=%s AND type=%s""", (amount, userid, acctype))
            if res is not None:
                print(res)
        except Exception as e:
            print(e)


def list_users(conn):
    """
    List all users
    """
    print('\n\nListing all users')
    with conn.cursor() as curs:
        try:
            curs.execute('SELECT * from users')
            rows = curs.fetchall()
            print('Number of results:', curs.rowcount)
            for row in rows:
                print(row)
        except Exception as e:
            print(e)

    
def show_accounts(conn, userid):
    """
    Lists account statement for a given userid
    """
    print('\n\nAccount statment for user', (userid))
    with conn.cursor() as curs:
        try:
            curs.execute('SELECT id, type, balance FROM accounts WHERE owner_id=%s', (userid,))
            rows = curs.fetchall()
            print('Number of results:', curs.rowcount)
            for row in rows:
                print(row)
        except Exception as e:
            print(e)


def main(options):
    try:
        DIR = os.path.dirname(__file__)
        configpath = os.path.join(DIR, './config/db-connection.json')
        # All subsequent Database operations in this script are performed on this connection
        conn = connect_to_db(configpath)

        # Operations on a connection is performed by the cursors from connection
        # Every connections starts a new transaction unless committed or rollback
        # So no matter the first cursor performing a execute or subsequent cursor
        # All the executions will not be persisted to Database unless committed

        # By default even a simple SELECT will start a transaction: in long-running programs, 
        # if no further action is taken, the session will remain “idle in transaction”, 
        # an undesirable condition for several reasons (locks are held by the session, tables bloat…). 
        # For long lived scripts, either make sure to terminate a transaction 
        # as soon as possible or use an autocommit connection

        if len(options) > 0 and options[0] == '--flush':    
            schemapath = os.path.join(DIR, './schema.sql')
            create_schema(conn, schemapath)
            feedpath = os.path.join(DIR, './dogfeed.sql')
            dogfeed(conn, feedpath)

        # Lists all the users, but also initiates a transaction
        list_users(conn)
        # Still in transaction
        show_accounts(conn, 1)

        # Raises a constraint exception, due to negative amount
        make_deposit(conn, 1, 'savings', -130.00)

        # current transaction is aborted, commands ignored until end of transaction block
        make_deposit(conn, 1, 'savings', 130.00) # this command, as well as any subsequent command has no effect, a rollback has to be made

        # Rollback needs to be called to end the transaction and start a new one.
        conn.rollback()
        
        make_deposit(conn, 1, 'savings', 130.00)
        # Commit persists the update to database
        conn.commit()

        # Lists the account statement for user 1, but also initiates a transaction
        show_accounts(conn, 1)

    except Exception as e:
        print(e)
    finally:
        if conn is not None:
            conn.close()


if __name__ == '__main__':
    options = []
    if len(os.sys.argv) > 1:
        options = os.sys.argv[1: len(os.sys.argv)]
        if options[0] == '--help':
            print("""Usage:
                python basic.py --help
                python basic.py
                python basic.py --flush
            """)
            exit()
    main(options)
