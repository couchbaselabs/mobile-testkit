# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure(2) do |config|

  host_ips = [
    "host1",
    "host2",
    "host3",
    "host4"
  ]

  host_ips.each do |host_name|
      config.vm.define host_name do |host|
        host.vm.box = "centos/6"
        config.vm.network "public_network", bridge: "en0: Wi-Fi (AirPort)"
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

