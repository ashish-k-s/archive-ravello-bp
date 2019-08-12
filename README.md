# archive-ravello-bp
Tool to archive disk images and metadata of your blueprint on Ravello cloud and store it locally.
Local backup of Ravello blueprint is useful for migration from Ravello to other cloud environment.

## Objective

Create local archive of Ravello blueprints for migration in other cloud infrastructure.
Setup

- Install the package:
```
    # rpm -ivh archive-ravello-bp-1.0-0.x86_64.rpm

    or

    # tar -zxvf archive-ravello-bp-1.0-0.tar.gz

    # cd archive-ravello-bp-1.0-0

    # ./setup
```
- Make sure ravello sdk is installed on the system
- post-install script of rpm package or setup utility does it for you
```
    # pip list | grep ravello

    Set Ravelloi login credentials using –set-login option to the script

    $ archive-ravello-bp.py –set-login
    Enter username: <ravello-user-id>

    Enter a Password:

    Login credentials are set, you may now use this script for archiving your blueprints
    $ ls -l ~/.ravello_login
```
   - If credentials are not set, the username can be specified using -u option
   - Upload archive-server disk image and archive-client iso to Ravello.
   - Probe archive-server disk and archive-client iso image parameters
```
    $ archive-ravello-bp.py –image archive-server-image
    DEBUG: Reading login credentials from: /home/user/.ravello_login
    DEBUG: Reading configuration file /etc/archive-ravello-bp.ini
    Image name: archive-server-image
    Image id: 3123532529856
    Image size: 9
    Image size unit: GB

    $ archive-ravello-bp.py –image archive-client.iso
    DEBUG: Reading login credentials from: /home/user/.ravello_login
    DEBUG: Reading configuration file /etc/archive-ravello-bp.ini
    Image name: archive-client.iso
    Image id: 3123532497086
    Image size: 602428
    Image size unit: KB
```
- Configure /etc/archive-ravello-bp.ini configuration file with appropriate image name, id and image size.
```
    # vi /etc/archive-ravello-bp.ini

    . . .

    [disk_client]

    . . .

    baseDiskImageName = archive-client.iso

    baseDiskImageId = 3123532497086
    size_value = 602428

    . . .

    [disk_server]

    . . .

    baseDiskImageName = archive-server-image

    baseDiskImageId = 3123532529856
    size_value = 9

    . . .
```
Refer to the steps mentioned under Miscellaneous tasks section below for detailed steps for creating and uploading archive server and client images.

## How to run

- Execute archive-ravello-bp.py script as below:
```
    $ archive-ravello-bp.py -b my-blueprint –start
```
## Result

- Blueprint’s design related metadata is available on the system running python script.

- The file with name APPNAME-orig.json (replace APPNAME with actual application being run) is available in present working directory.
```
    $ ls my-blueprint-ARCHIVE-*
```
- Disk images (qcow2 and iso) belonging to all the VMs are available within the Ravello application on archive-server VM attached by this script to the application.

- Files are in /data/ directory on archive server.

- The disk image files are named as APPNAME-VMNAME-disk.qcow2 (replace APPNAME and VMNAME as actual)a

- The iso image files are named as APPNAME-VMNAME-disk.iso (replace APPNAME and VMNAME as actual)
```
    [root@data-server ~]# ll /data/
```
## Download

- Source

https://github.com/ashish-k-s/archive-ravello-bp

- RPM package / Tarball

- Disk Images

## What this package contains?

/usr/local/bin/archive-ravello-bp.py : The actual script to be run to archive the blueprint

/etc/archive-ravello-bp.ini : Self documented configuration file for archive-ravello-bp tool.
/usr/local/bin/common.py : Common tasks used in above script. This file is provided by Ravello along with it’s SDK
/usr/share/doc/archive-ravello-bp-doc/README : Documentation of the project
/usr/share/doc/archive-ravello-bp-doc/sample/ : Sample json file and hand-written heat template file using captured details.

/usr/share/doc/archive-ravello-bp-doc/scripts/ : Custom startup scripts, service file and kickstart file which can be used with this project.

## How it works

- There are three components involved with this automation process.

  -  Python script (running on your laptop/desktop)
  -  Archive client iso image (in Ravello cloud)
  -  Archive server disk image (in Ravello cloud)

Python script is executed with name of blueprint to be archived.

The blueprint is then launched in Ravello cloud environment and few automated tasks are performed on resulting client application to create archive.

Archive client iso is automatically attached to all the VMs of the application to capture it’s disk images

Archive server VM is attached to the application to collect disk images of all (client) VMs. The archive server disk is attached to the Ravello server VM. Additional data disk is attached to the server VM to collect disk backups. Size of required disk space to collect the data is automatically calculated by this script.
Tasks performed by involved components

### Python script

- Launches application for provided blueprint
- Stores the metadata useful for migration process
- Modifies the archive application to:
  -  Attach ravello client iso to all the VMs in application
  -  Calculate disk space required to collect archive of all VMs
  -  Wipe network configuration of all the VMs of the archive application
  -  Add new network configuration to all the VMs
  -  Inject cloud init script to all vms to pass few configuration details
  -  Add archive server VM to the archive application
  -  Attach archive server disk image to archive server to boot-up.
  -  Attach additional disk (of size calculated earlier) to archive server to collect archive data
- Updates application with new metadata
- Publishes application to the region configured as per configuration file

### Archive client iso

This iso image is attached to all the VMs of the application and the VMs are booted using this iso image.

Startup scripts in iso image mounts an nfs share from archive server VM running within this application
and then does the job of archiving hard disk images of the vms to archive server hosted within the application.
Archive server VM

This VM is attached to the application. It acts as archive server who collects archive data from all the VMs of the application.

First job of archive server is to check the data drive attached to it. If it is not formatted, then format it and mount it locally.

If the data drive is already formatted, mount it locally on the directory shared via nfs to store archive images in it.

## Miscellaneous tasks

### Ravello SDK

- This tool requires Ravello’s python SDK installed on the system.

- Make sure the SDK file is available at below path:
```
    /usr/lib/python2.7/site-packages/ravello_sdk.py
```
### Create bootable ISO image for archive client

- Login as root on RHEL7 / CentOS7 / Feora system
- Download installer DVD ISO image
- Install Live media creator package on the system
```
    # yum install lorax

    or

    # dnf install lorax
```
Download the kickstart file build-iso.ks available in the package
Or make copy of sample file and modify it
```
cp /usr/share/doc/lorax-19.7.19/rhel7-minimal.ks .
```
    Disable selinux
```
    setenforce 0
```
    After modifying the kickstart file, create custom bootable iso image using it.
```
    livemedia-creator –make-iso –iso=YOUR-OS-MEDIA-DISK.iso –ks=build-iso.ks –no-virt
```
    Copy boot.iso from generated /var/tmp/tmp* directory to /root/
```
    Example:
    # livemedia-creator –make-iso –iso=YOUR-OS-MEDIA-DISK.iso –ks=build-iso.ks –no-virt
    2019-02-27 12:39:49,522: livemedia-creator 19.7.19-1

    . . .

    2019-02-27 12:47:06,803: Logs are in /root
    2019-02-27 12:47:06,803: Results are in /var/tmp/tmp5f7cuy
    # cp /var/tmp/tmp5f7cuy/images/boot.iso /root/
```

Modify ISO image to add custom scripts

### Modify iso image to add or modify custom scripts in it

- Mount iso on an empty directory and copy it’s contents to another directory.
```
    # mkdir mnt

    # mount boot.iso mnt

    # mkdir iso

    # cp -pRf mnt/* iso/
```
- Make required modification to copied contents of iso
- Change default boot option by modifying isolinux.cfg file
```
    # cd iso
    # vi isolinux/isolinux.cf
```
### Modify contents of live OS image
```
    # cd LiveOS/
    # unsquashfs squashfs.img
    # cd squashfs-root/LiveOS/
    # mkdir img
    # mount rootfs.img img/
    # cd img/
```
- Make necessary modification in this (img) directory. It is the root partition upon bootup using iso.
- Copy required files like systemd startup scripts, custom scripts and binaries here
- The changes could be like modifying startup service files or adding or modifying startup scripts, etc
```
    # cd usr/local/bin/
    # vi get-disk-image.sh
    # vi nfs-mount.sh
    # vi startup.sh
    # chmod +x *

    # cd ../..
    # cd ..
    # vi etc/systemd/system/multi-user.target.wants/last-start.service
    # cd ..

    NOTE: All paths above are relative to img directory, make sure not to modify files on host system
```
- Unmount the image file from img directory and remove the img directory
```
    # umount img/

    # rmdir img/
```
- Make squash file with modified contents and remove squashfs-root directory after making squash file from it
```
    # cd ..
    # mv squashfs.img /tmp/
    # mksquashfs squashfs-root/ squashfs.img -noappend -always-use-fragments

    # rm -rf squashfs-root/
```
   - Get out of the copied iso contents directory and make new iso file from it.
```
    # cd ..
    # mkisofs -allow-limited-size -l -J -r -iso-level 3 -o ~/archive-client.iso -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -iso-level 3 -J -R -V “Red Hat Enterprise Linux 7 x86_6” .
```
### Upload ISO to ravello

- Upload the iso image generated in above steps to ravello cloud
```
    ./ravello import-disk -u <ravello-user-id> –disk /tmp/archive-client.iso
```
This iso image will be attached to all the VM of the blueprint being archived to captured disk image from those VMs.

### Archive server configuration

    - Create an application with one RHEL or CentOS or Fedora server in it.
    - Configure the RHEL VM as nfs server
    - Copy required startup scripts in the VM and do all necessary modifications
    - Shutdown the VM
    - Save the VM’s disk image in Ravello’s liverary.
    - This VM image will be attached to the archive server injected by the script in blueprint being archived.

## Report Bugs

Report bugs to ashish.k.shah@gmail.com
