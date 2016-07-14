#!/usr/bin/python

import os, sys, errno
from subprocess import check_call
import usage
from generate_html import generate_html

def setup():
    # generate a random password
    certs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'certs'))
    cert_pwd = os.path.join(certs_dir, 'cert_pwd')
    cmd = 'date +%%s | sha256sum | base64 | head -c 32 > %s' % cert_pwd
    check_call(cmd, shell=True)

    # initialize certificate
    home_dir = os.path.abspath(os.path.expanduser('~'))
    nssdb_dir = os.path.join(home_dir, '.pki/nssdb')
    # create nssdb directory if it doesn't exist
    try:
        os.makedirs(nssdb_dir)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    cmd = 'certutil -d %s -N -f %s' % (nssdb_dir, cert_pwd)
    check_call(cmd, shell=True)

    # generate certificate
    certs_proc = check_call(['./generate-certs.sh'], cwd=certs_dir)

    # trust certificate
    pem = os.path.join(certs_dir, 'out/2048-sha256-root.pem')
    cmd = 'certutil -d sql:%s -A -t "C,," -n "QUIC" -i %s -f %s' \
            % (nssdb_dir, pem, cert_pwd)
    check_call(cmd, shell=True)

    # generate a html of size that can be transferred longer than 60 seconds
    generate_html(50000000)

def main():
    usage.check_args(sys.argv, os.path.basename(__file__), usage.SEND_FIRST)
    option = sys.argv[1]
    src_dir = os.path.abspath(os.path.dirname(__file__))
    submodule_dir = os.path.abspath(os.path.join(src_dir,
                                    '../third_party/proto-quic'))
    find_unused_port_file = os.path.join(src_dir, 'find_unused_port')
    quic_server = os.path.join(submodule_dir, 'src/out/Release/quic_server')
    quic_client = os.path.join(submodule_dir, 'src/out/Release/quic_client')
    DEVNULL = open(os.devnull, 'wb')

    # build
    if option == 'build':
        os.environ['PATH'] += ':%s/depot_tools' % submodule_dir
        cmd = 'cd %s/src && gclient runhooks && ninja -C out/Release ' \
              'quic_client quic_server' % submodule_dir
        check_call(cmd, shell=True)

    # setup
    if option == 'setup':
        setup()
        sys.stderr.write("Sender first\n")

    # sender
    if option == 'sender':
        sys.stderr.write("Listening on port: 6121\n")
        cmd = [quic_server,
              '--quic_in_memory_cache_dir=/tmp/quic-data/www.example.org',
              '--certificate_file=%s/certs/out/leaf_cert.pem' % src_dir,
              '--key_file=%s/certs/out/leaf_cert.pkcs8' % src_dir]
        check_call(cmd, stdout=DEVNULL, stderr=DEVNULL)

    # receiver
    if option == 'receiver':
        ip = sys.argv[2]
        port = sys.argv[3]
        cmd = [quic_client, '--host=%s' % ip, '--port=%s' % port,
              'https://www.example.org/']
        check_call(cmd, stdout=DEVNULL, stderr=DEVNULL)

    DEVNULL.close()

if __name__ == '__main__':
    main()