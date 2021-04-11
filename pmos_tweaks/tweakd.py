import os
import configparser
from pmos_tweaks.settingstree import SettingsTree


def main(version, datadir=None):
    # Read settings yaml files to build a whitelist of settings that are allowed to change
    st = SettingsTree()
    if datadir is not None:
        st.load_dir(os.path.join(datadir, 'postmarketos-tweaks'))
    st.load_dir('/etc/postmarketos-tweaks')
    settings = st.settings

    whitelist_sysfs = []

    for page in settings:
        for section in settings[page]['sections']:
            for setting in settings[page]['sections'][section]['settings']:
                s = settings[page]['sections'][section]['settings'][setting]
                if s.backend == 'sysfs':
                    whitelist_sysfs.append(s.key)

    # Read the stored settings and apply them
    config = configparser.ConfigParser()
    config.read('/etc/postmarketos-tweaks/tweakd.conf')

    # Apply sysfs settings
    if config.has_section('sysfs'):
        for path in config.options('sysfs'):
            if path not in whitelist_sysfs:
                print(f"Skipping {path}, not defined in setting definitions")
            value = config.get('sysfs', path)
            print(f"{path} = {value}")
            with open(path, 'w') as handle:
                handle.write(value)


if __name__ == '__main__':
    main(None)
