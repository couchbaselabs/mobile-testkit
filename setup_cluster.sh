#!/usr/bin/env bash

vagrant reload

ssh-add .vagrant/machines/host1/virtualbox/private_key
ssh-add .vagrant/machines/host2/virtualbox/private_key
ssh-add .vagrant/machines/host3/virtualbox/private_key
ssh-add .vagrant/machines/host4/virtualbox/private_key