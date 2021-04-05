pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'pmos_tweaks')
gnome = import('gnome')

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)
conf.set('datadir', join_paths(get_option('prefix'), get_option('datadir')))

configure_file(
    input: 'pmos-tweaks.in',
    output: 'pmos-tweaks',
    configuration: conf,
    install: true,
    install_dir: get_option('bindir')
)

sources = [
    '__init__.py',
    '__main__.py',
    'window.py',
    'settingstree.py',
]

install_data(sources, install_dir: moduledir)
