# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure(2) do |config|

  config.vm.define "host1" do |host1|
    host1.vm.box = "centos/7"
    host1.vm.network "private_network", ip: "192.168.33.10"
    host1.ssh.insert_key = false

    host1.vm.provider "virtualbox" do |vb|
        # Customize the amount of memory on the VM:
        vb.memory = "2048"
    end
  end

  config.vm.define "host2" do |host2|
    host2.vm.box = "centos/7"
    host2.vm.network "private_network", ip: "192.168.33.11"
    host2.ssh.insert_key = false

    host2.vm.provider "virtualbox" do |vb|
        # Customize the amount of memory on the VM:
        vb.memory = "2048"
    end
  end

  config.vm.define "host3" do |host3|
    host3.vm.box = "centos/7"
    host3.vm.network "private_network", ip: "192.168.33.12"
    host3.ssh.insert_key = false

    host3.vm.provider "virtualbox" do |vb|
        # Customize the amount of memory on the VM:
        vb.memory = "2048"
    end
  end

  config.vm.define "host4" do |host4|
    host4.vm.box = "centos/7"
    host4.vm.network "private_network", ip: "192.168.33.13"
    host4.ssh.insert_key = false

    host4.vm.provider "virtualbox" do |vb|
        # Customize the amount of memory on the VM:
        vb.memory = "2048"
    end
  end

end
