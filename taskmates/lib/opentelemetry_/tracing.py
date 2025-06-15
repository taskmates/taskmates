from opentelemetry.instrumentation.auto_instrumentation import _load_distro, _load_configurators, _load_instrumentors


def auto_instrument():
    distro = _load_distro()
    distro.configure()
    _load_configurators()
    _load_instrumentors(distro)
