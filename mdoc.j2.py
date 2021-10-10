import datetime


def me():
    return "\n.Nm\n"


def now():
    return datetime.datetime.now().strftime("%B %d, %Y")


def option(name, end=None):
    return "Fl Fl {:}".format(name if not end else "{:} {:}".format(name, end))


def envvar(name, val=None, end=None):
    if not val:
        return "Ev {:}".format(name if not end else "{:} {:}".format(name, end))
    else:
        return "Pf {:}= {:}".format(name, arg(val, end))


def synopsis(form):
    out = []
    for arg in form:
        line = "."
        if "optional" in arg:
            line += "Op "
        if "name" in arg:
            line += "Ar " + arg["name"]
        else:
            line += "No " + arg
        out.append(line)
    return me() + "\n".join(out)


def arg(name, end=None):
    """ """
    return "Ar {:}".format(name if not end else "{:} Ns {:}".format(name, end))


def literal_arg(name, end=None):
    """
    Not sure it's the right semantic, but .Cm is the command macro.
    Roughly equivalent to .Fl except it doesn't append the -. That
    seems to match our usage here...
    """
    return "Cm {:}".format(name if not end else "{:} {:}".format(name, end))


import subprocess, jinja2


def inline(path, indent=0):
    spaces = " " * indent
    return jinja2.Markup(
        subprocess.run(
            ["sed", "-e", "s/^/" + spaces + "/", path],
            capture_output=True,
            text=True,
        ).stdout[
            indent:
        ]  # .lstrip()
    )


def j2_environment(env):
    """Modify Jinja2 environment
    :param env: jinja2.environment.Environment
    :rtype: jinja2.environment.Environment
    """
    env.globals.update(
        me=me,
        envvar=envvar,
        option=option,
        literal_arg=literal_arg,
        arg=arg,
        inline=inline,
        now=now,
        synopsis=synopsis,
    )
    return env
