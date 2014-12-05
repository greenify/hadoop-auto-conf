#!/bin/bash
fab -R master install config
fab -R client -P install config
fab -R master updateClients
fab -R client -P updateClients
fab -R master start
fab -R master hdfsTest
