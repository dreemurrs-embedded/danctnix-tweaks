project('danctnix-tweaks',
    version: '0.13.1',
    meson_version: '>= 0.50.0',
    default_options: ['warning_level=2'])

dependency('libhandy-1', version: '>=1.5.0')

subdir('data')
subdir('danctnix_tweaks')

install_subdir('settings',
        install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'danctnix-tweaks'),
        strip_directory: true)

meson.add_install_script('build-aux/meson/postinstall.py')
