# deploy/core/ssh_executor.py
import paramiko
from pathlib import Path
import stat

class SSHExecutor:
    def __init__(self, host, username, private_key_path):
        self.host = host
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        key = paramiko.RSAKey.from_private_key_file(private_key_path)
        self.client.connect(host, username=username, pkey=key)
    
    def run_command(self, command):
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode(), stderr.read().decode()
    
    def create_directory(self, path, mode=0o755):
        """جایگزین create-dirs task"""
        sftp = self.client.open_sftp()
        try:
            sftp.mkdir(path)
            sftp.chmod(path, mode)
        except:
            pass
    
    def copy_file(self, local_path, remote_path):
        """جایگزین copy ماژول Ansible"""
        sftp = self.client.open_sftp()
        sftp.put(local_path, remote_path)