#!/usr/bin/python
import commands
import subprocess
import urllib
import tarfile
import time
import os
import hashlib
import shutil

def check_requirements():
  ipset_status = commands.getstatusoutput("hash ipset")
  iptables_status = commands.getstatusoutput("hash iptables")
  if ipset_status[0] != 0 or iptables_status[0] != 0:
    raise Exception("Iptables and/or ipset not found, please intstall these dependencies first")

def md5_for_file(f):
  md5 = hashlib.md5()
  for ip in f:
    md5.update(ip)
  return md5.hexdigest()

def retrieve_whitelist():
  whitelist = urllib.urlopen("http://reliablenameservers.org/whitelists/latest_whitelist")
  temp_path = "/tmp/whitelist/%d" % int(time.time())
  temp_name = os.path.join(temp_path, "latest_whitelist")
  os.makedirs(temp_path)
  temp = open(temp_name, "wr")
  temp.write(whitelist.read())
  temp.flush()
  temp.close()

  temp = open(temp_name)
  tar = tarfile.open(mode="r:gz", fileobj=temp)
  tar.extractall(temp_path)

  latest_whitelist = open(os.path.join(temp_path, "whitelist"), "r")

  if md5_for_file(latest_whitelist) != open(os.path.join(temp_path, "whitelist.md5")).read():
    raise Exception("Download seems to be corrupt, please run again.")

  return latest_whitelist

def fill_ipset(latest_whitelist):
  subprocess.call(["ipset", "create", "whitelist", "hash:ip", "maxelem", "1000000"])
  latest_whitelist.seek(0)
  for ip in latest_whitelist:
    subprocess.call(["ipset", "add", "whitelist", ip])

def add_iptables_rules():
  subprocess.call("iptables -A INPUT -p udp --dport 53 -m set --match-set whitelist src -j ACCEPT", shell=True)
  subprocess.call("iptables -A INPUT -p udp --dport 53 -m recent --rcheck --seconds 10 --hitcount 2 --name GREYLIST -j DROP", shell=True)
  subprocess.call("iptables -A INPUT -p udp --dport 53 -m recent --set --name GREYLIST -j ACCEPT", shell=True)

def cleanup():
  shutil.rmtree(temp_path)

if __name__ == '__main__':
  print "Reliable Nameserver installer"
  check_requirements()
  print "Download latest whitelist",
  latest_whitelist = retrieve_whitelist()
  print " - Done"
  print "Add whitelisted IPs to ipset",
  fill_ipset(latest_whitelist)
  print " - Done"
  iptables = ""
  while iptables.lower() not in ["y", "n"]:
    iptables = raw_input("Let installer add iptable rules? (y/n): ")
  if iptables.lower() == "y":
    print "Add iptables rules",
    add_iptables_rules()
    print " - Done"
