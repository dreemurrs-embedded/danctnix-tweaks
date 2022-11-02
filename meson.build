project('pmos-tweaks',
    version: '0.12.0',
    meson_version: '>= 0.50.0',
    default_options: ['warning_level=2'])

dependency('libhandy-1', version: '>=1.5.0')

subdir('data')
subdir('pmos_tweaks')

install_subdir('settings',
        install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'postmarketos-tweaks'),
        strip_directory: true)

meson.add_install_script('build-aux/meson/postinstall.py')
