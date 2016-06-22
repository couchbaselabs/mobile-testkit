# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure(2) do |config|

  host_ip = {
    "host1" => "192.168.33.10",
    "host2" => "192.168.33.11",
    "host3" => "192.168.33.12",
    "host4" => "192.168.33.13",
  }

  host_ip.each do |host_name, ip|
      config.vm.define host_name do |host|
        host.vm.box = "centos/7"
        host.vm.network "private_network", ip: ip
        host.vm.synced_folder ".", "/home/vagrant/sync", disabled: true
        host.vm.provider "virtualbox" do |vb|
            # Customize the amount of memory on the VM:
            vb.memory = "2048"

            # Allow vm to send data via VPN
            vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
        end
      end
  end

end

