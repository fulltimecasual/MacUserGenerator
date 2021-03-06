#!/usr/bin/env python

"""Description goes here"""

import os
import platform
import plistlib
import stat
import subprocess
import sys
import uuid
# pylint: disable=E0611
from OpenDirectory import ODSession, ODNode, kODNodeTypeLocalNodes, kODRecordTypeUsers
# pylint: enable=E0611

PLIST_PATH = "/private/var/db/dslocal/nodes/Default/users/"

USER_DATA = {
    "authentication_authority": ";ShadowHash;HASHLIST:<SALTED-SHA512-PBKDF2>",
    "generateduid":             str(uuid.uuid4()).upper(),
    "gid":                      "20",
    "IsHidden":                 "#ISHIDDEN",
    "home":                     "#HOME",
    "name":                     "#NAME",
    "passwd":                   "********",
    "realname":                 "#REALNAME",
    "ShadowHash":               """#SHADOWHASH""",
    "shell":                    "#SHELL",
    "uid":                      "#UID",
    "_writers_hint":            "#NAME",
    "_writers_jpegphoto":       "#NAME",
    "_writers_passwd":          "#NAME",
    "_writers_picture":         "#NAME",
    "_writers_realname":        "#NAME",
    "_writers_UserCertificate": "#NAME"
}

USER_PREFERENCES = {
    "admin":              "#ADMIN",
    "autologin":          "#AUTOLOGIN",
    "kcpassword":         "#KCPASSWORD",
    "skipsetupassistant": "#SKIPSETUPASSISTANT"
}


def is_booted_volume():
    """Description"""

    if len(sys.argv) < 4:
        return True

    target = sys.argv[3]
    local_disk = "/"
    return target is local_disk


def get_target():
    """Description"""

    target = sys.argv[3]
    local_disk = "/"
    return "" if target == local_disk else target


def get_od_node():
    """Description"""

    session = ODSession.defaultSession()

    if not session:
        return None

    node, error = ODNode.nodeWithSession_type_error_(
        session, kODNodeTypeLocalNodes, None
    )

    if error:
        print >> sys.stderr, error
        return None

    return node


def record_exists(name):
    """Description"""

    if is_booted_volume():
        node = get_od_node()

        if not node:
            return False

        record, error = node.recordWithRecordType_name_attributes_error_(
            kODRecordTypeUsers,
            name,
            None,
            None
        )

        if error:
            print >> sys.stderr, error
            return False

        return record is not None
    else:
        path = get_target() + PLIST_PATH + name + ".plist"
        return os.path.isfile(path)


def create_record(user_data):
    """Description"""

    print "User record '" + user_data["name"] + "' does not exist"

    if is_booted_volume():
        node = get_od_node()

        if not node:
            return

        record, error = node.createRecordWithRecordType_name_attributes_error_(
            kODRecordTypeUsers,
            user_data["name"],
            None,
            None
        )

        if error:
            print >> sys.stderr, error
            return

        print "User record '" + user_data["name"] + "' created via Open Directory"
    else:
        dictionary = {"name": user_data["name"]}
        path = get_target() + PLIST_PATH + user_data["name"] + ".plist"
        plistlib.writePlist(dictionary, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        print "User record '" + user_data["name"] + "' created via Property List"


def update_record(user_data):
    """Description"""

    if is_booted_volume():
        node = get_od_node()

        if not node:
            return

        record, error = node.recordWithRecordType_name_attributes_error_(
            kODRecordTypeUsers,
            user_data["name"],
            None,
            None
        )

        print "User record '" + user_data["name"] + "' exists"

        if error:
            print >> sys.stderr, error
            return

        for attribute, value in user_data.items():

            if attribute == "ShadowHash":
                continue

            success, error = record.setValue_forAttribute_error_(
                value,
                attribute,
                None
            )

            if error:
                print >> sys.stderr, error
                return

            print "User record '" + user_data["name"] + "' updated attribute " + \
                attribute + ": " + str(value)

        print "User record '" + user_data["name"] + "' updated via Open Directory"
    else:
        path = get_target() + PLIST_PATH + user_data["name"] + ".plist"
        plist = plistlib.readPlist(path)

        print "User record '" + user_data["name"] + "' exists"

        for attribute, value in user_data.items():

            if attribute == "ShadowHash":
                continue

            plist[attribute] = value

            print "User record '" + user_data["name"] + "' updated attribute " + \
                attribute + ": " + str(value)

        plistlib.writePlist(plist, path)
        print "User record '" + user_data["name"] + "' updated via Property List"


def set_shadowhash(name, shadowhash):
    """Description"""

    path = get_target() + PLIST_PATH + name + ".plist"
    command = "Remove :ShadowHashData:0"
    subprocess.call(["/usr/libexec/plistbuddy", "-c", command, path])
    command = "Add :ShadowHashData:0 string " + "..." + shadowhash + "..."
    subprocess.call(["/usr/libexec/plistbuddy", "-c", command, path])
    filehandler = open(path, 'r')
    plist = filehandler.read()
    filehandler.close()
    plist = plist.replace('<string>...', '<data>')
    plist = plist.replace('...</string>', '</data>')
    filehandler = open(path, 'w')
    filehandler.write(plist)
    filehandler.close()
    print "User record '" + name + "' updated attribute ShadowHash"


def set_admin(state, name, generateduid):
    """Description"""

    if is_booted_volume():
        membertype = "-a" if state == "TRUE" else "-d"
        subprocess.call(["dseditgroup", "-o", "edit", membertype, name, "-t", "user", "admin"])
        print ("Set" if state else "Removed") + " Admin for user record '" + name + "'"
    else:
        print "plist method"


def set_autologin(name, kcpassword):
    """Description"""


def create_home_directory(name):
    """Description"""

    subprocess.call(["createhomedir", "-c", "-u", name])
    print "Created user record '" + name + "' home folder"


def skip_setup_assistant(name, home):
    """Description"""

    path = "/private/var/db/.AppleSetupDone"
    subprocess.call(["touch", path])
    path = home + "/Library/Preferences/com.apple.SetupAssistant.plist"

    command = "Add :DidSeeCloudSetup bool TRUE"
    subprocess.call(["/usr/libexec/plistbuddy", "-c", command, path])
    print "Skipped Setup Assistant: iCloud"

    command = "Add :DidSeeSiriSetup bool TRUE"
    subprocess.call(["/usr/libexec/plistbuddy", "-c", command, path])
    print "Skipped Setup Assistant: Siri"

    command = "Add :DidSeeTouchIDSetup bool TRUE"
    subprocess.call(["/usr/libexec/plistbuddy", "-c", command, path])
    print "Skipped Setup Assistant: Touch ID"

    productversion = platform.mac_ver()[0]
    buildversion = os.popen("sw_vers -buildVersion").read().strip()
    command = "Add :LastSeenCloudProductVersion string " + productversion
    subprocess.call(["/usr/libexec/plistbuddy", "-c", command, path])
    command = "Add :LastSeenBuddyBuildVersion string " + buildversion
    subprocess.call(["/usr/libexec/plistbuddy", "-c", command, path])
    print "Skipped Setup Assistant: Analytics"

    command = "Add :DidSeePrivacy bool TRUE"
    subprocess.call(["/usr/libexec/plistbuddy", "-c", command, path])
    print "Skipped Setup Assistant: Data & Privacy"

    subprocess.call(["chown", name, path])
    subprocess.call(["chmod", "600", path])
    print "Set correct ownership and permissions on " + path

def restart_directory_services():
    """Description"""

    subprocess.call(["killall", "DirectoryService"])
    subprocess.call(["killall", "opendirectoryd"])
    print "Restarted Directory Services"


def main():
    """Description"""

    if not record_exists(USER_DATA["name"]):
        create_record(USER_DATA)

    update_record(USER_DATA)
    set_shadowhash(USER_DATA["name"], USER_DATA["ShadowHash"])
    set_admin(USER_PREFERENCES["admin"], USER_DATA["name"], USER_DATA["generateduid"])
    set_autologin(USER_DATA["name"], USER_PREFERENCES["kcpassword"])
    create_home_directory(USER_DATA["name"])

    if USER_PREFERENCES["skipsetupassistant"] == "TRUE":
        skip_setup_assistant(USER_DATA["name"], USER_DATA["home"])

    restart_directory_services()


if __name__ == '__main__':
    main()
