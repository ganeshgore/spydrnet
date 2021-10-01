import sys
from IPython.terminal.ipapp import load_default_config
from IPython.terminal.prompts import Prompts, Token
from IPython.terminal.embed import InteractiveShellEmbed
from IPython.core.interactiveshell import InteractiveShell


class MyPrompt(Prompts):
    def in_prompt_tokens(self, cli=None):
        return [(Token, "PhyFloTa"),
                (Token.Prompt, ' >>> ')]


def launch_shell(**kwargs):
    config = load_default_config()
    config.InteractiveShellEmbed = config.TerminalInteractiveShell
    kwargs['colors'] = "neutral"
    kwargs['config'] = config
    using = kwargs.get('using', 'sync')
    if using:
        kwargs['config'].update({'TerminalInteractiveShell': {
                                'loop_runner': using,
                                'colors': 'NoColor',
                                'autoawait': using != 'sync'}})

    kwargs['config'].update({'InteractiveShell': {'prompts_class': MyPrompt}})
    kwargs['banner1'] = "Launching interactive mode"

    saved_shell_instance = InteractiveShell._instance
    if saved_shell_instance is not None:
        cls = type(saved_shell_instance)
        cls.clear_instance()
    frame = sys._getframe(1)
    shell = InteractiveShellEmbed.instance(_init_location_id='%s:%s' % (
        frame.f_code.co_filename, frame.f_lineno), **kwargs)
    shell(header="", stack_depth=2, compile_flags=None,
          _call_location_id='%s:%s' % (frame.f_code.co_filename, frame.f_lineno))
    InteractiveShellEmbed.clear_instance()
    # restore previous instance
    if saved_shell_instance is not None:
        cls = type(saved_shell_instance)
        cls.clear_instance()
        for subclass in cls._walk_mro():
            subclass._instance = saved_shell_instance
