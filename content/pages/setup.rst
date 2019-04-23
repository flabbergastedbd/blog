my setup
########

:date: 2019-04-22
:modified: 2019-04-23
:summary: An up-to-date page describing my setup

.. contents::

.. note::

        This text should describe my current setup including hardware and software. If you have alternatives
        that  you want me to try, please comment below. I would love to hear about alternatives. Configuration for
        any of my settings if public will either be present in my dotfiles_ or hermes_ (terraform self hosted configurations)


Hardware
********

Machines
========

* MacbookPro 2017
* Dell XPS 13 9350
* `Desktop <https://in.pcpartpicker.com/list/4Yr6Cy>`_

Accessories
===========

.. table::
        :widths: auto
        :class: pure-table pure-table-horizontal

        ============== ============================================================================================================
        Monitors        `HP 22FI <https://www.amazon.in/HP-22FI-IPS-LED-Monitor/dp/B00HVU4PIA>`_, `HP 22ES <https://www.amazon.in/HP-21-5-inch-54-6-Monitor/dp/B01F8LCALM/>`_
        Keyboard        `Corsair Strafe Red <https://www.amazon.com/CORSAIR-STRAFE-Mechanical-Gaming-Keyboard/dp/B00ZUPOMDQ>`_
        Mouse           `Logitech G350s <https://www.amazon.com/Logitech-G300s-Optical-Ambidextrous-Gaming/dp/B00RH6R7C4/>`_
        Speakers        `Logitech Z625 <https://www.amazon.in/Logitech-Z625-Powerful-Speaker-Black/dp/B01JPOLLKE/>`_
        Earphones       `Sony MDR-XB55AP <https://www.amazon.in/Sony-MDR-XB55AP-Extra-Headphone-Black/dp/B073JPC6R3/>`_
        Mat             `Corsair MM300 <https://www.amazon.in/Corsair-CH-9000108-WW-Extended-Anti-Fray-Gaming/dp/B01798VS4C>`_
        ============== ============================================================================================================

Software
********

Operating Systems
=================

MacOS, Linux majorly. All development and work happens on these two. My desktop also boots Windows for Steam and Origin gaming.

Linux
=====

.. table::
        :widths: auto
        :class: pure-table pure-table-horizontal

        =============== ===========================================
        Distribution    `Arch Linux <https://www.archlinux.org/>`_
        Window Manager  `bspwm <https://github.com/baskerville/bspwm>`_
        X daemon        `sxhkd <https://github.com/baskerville/sxhkd>`_
        Emulator        `termite <https://github.com/thestinger/termite>`_
        Compositor      `compton <https://github.com/chjj/compton>`_
        =============== ===========================================

Common
======

.. table::
        :widths: auto
        :class: pure-table pure-table-bordered

        =============== =======================================================================================================================================================
        fish_            I find fish shell to be the python of shells. It is super easy to use and customizing it is a bliss. I use omf_ to handle fish plugins & use batman_ as
                         my fish theme.
        vim_             There cannot be a substitute for this, my entry into world of cli. LEGENDARY!!
        tmux_            It is impossible for me to work without tmux, I have a status line that is suited for me.
        neomutt_         Vanilla neomutt is my email client, use it with plain imap.
        weechat_         My irc+slack+matrix client, works superbly.
        taskwarrior_     Task list to keep track of things to do.
        mpd_ (ncmpcpp)   My music daemon and client, synced using rclone_.
        rclone_          Used for backing up things to cloud, things that I cannot push to public version control.
        buku_            For bookmarks, db is synced across devices using rclone_.
        pass_            Password manager with unix philosophy, synced across devices using rclone_.
        jq_              Swiss knife for json processing.
        peco_            Interactive filtering tool for terminal.
        stow_            Use it for managing my dotfiles_.
        aria2_           Multi-protocol download utility.
        youtube-dl_      Youtube downloader and conversion facility.
        terraform_       Infrastructure as code, used to maintain my cloud infrastructure.
        GNU              sed, awk, parallel
        =============== =======================================================================================================================================================

Replacements
============

.. table::
        :widths: auto
        :class: pure-table pure-table-bordered

        =============== =======================================================================================================================================================
        ls              exa_ (my ls and derivates are aliased to exa)
        Ctrl+R          fzf_ (used for directory naviation, history search via fish fzf bindings)
        cat             bat_ (nothing beats this)
        grep            ripgrep_ (very very fast, so fast that my vim is defaulted to use ripgrep)
        diff            diff-so-fancy_ (so fancy that my git is defaulted to use this diff utility)
        =============== =======================================================================================================================================================

Self Hosted
***********

Some of the following are on my desktop while some run on cloud.

.. table::
        :widths: auto
        :class: pure-table pure-table-bordered

        =============== =======================================================================================================================================================
        dokuwiki_       Wiki for collaboration.
        gitea_          Private git server.
        miniflux_       Feed collection and reader.
        znc_            IRC bouncer.
        transmission_   Torrent client.
        couchpotato_    Movie downloader.
        sickrage_       Tv/Anime downloader.
        headphones_     Music downloader.
        traefik_        Reverse proxy with excellent support for cloudflare dns and letsencrypt certs.
        osmc_           Runs on a raspberry pi3 connected to a tv via HDMI, allowing me to stream online content using kodi plugins & also to stream offline content from my desktop.
        emby_           Runs on my desktop and streams content to any device on my home network. Emby plugin is used in osmc to stream onto tv.
        =============== =======================================================================================================================================================

Images
******

This is how dark I generally work, with fancy rgb lights

.. image:: {static}/images/desktop-blue.png
        :scale: 50%

When my mom was curious about my keyboard

.. image:: {static}/images/desktop-mom.jpg
        :scale: 50%

More screenshots in dotfiles_.


.. _dotfiles: https://github.com/tunnelshade/awesome-dots
.. _omf: https://github.com/oh-my-fish/oh-my-fish
.. _batman: https://github.com/oh-my-fish/theme-batman
.. _rclone: https://rclone.org/
.. _taskwarrior: https://taskwarrior.org/
.. _buku: https://github.com/jarun/Buku
.. _neomutt: https://neomutt.org/
.. _weechat: https://weechat.org/
.. _tmux: https://github.com/tmux/tmux
.. _fish: https://fishshell.com/
.. _mpd: https://www.musicpd.org/
.. _pass: https://www.passwordstore.org/
.. _exa: https://github.com/ogham/exa
.. _fzf: https://github.com/junegunn/fzf
.. _bat: https://github.com/sharkdp/bat
.. _ripgrep: https://github.com/BurntSushi/ripgrep
.. _vim: https://www.vim.org/
.. _diff-so-fancy: https://github.com/so-fancy/diff-so-fancy
.. _aria2: https://aria2.github.io/
.. _jq: https://stedolan.github.io/jq/
.. _stow: https://www.gnu.org/software/stow/stow.html
.. _peco: https://github.com/peco/peco
.. _youtube-dl: https://github.com/ytdl-org/youtube-dl
.. _terraform: https://www.terraform.io/
.. _dokuwiki: https://www.dokuwiki.org/dokuwiki
.. _gitea: https://gitea.io/en-us/
.. _miniflux: https://miniflux.app/
.. _znc: https://wiki.znc.in/ZNC
.. _transmission: https://transmissionbt.com/
.. _couchpotato: https://couchpota.to/
.. _sickrage: https://www.sickrage.ca/
.. _headphones: https://github.com/rembo10/headphones
.. _traefik: https://traefik.io/
.. _osmc: https://osmc.tv/
.. _emby: https://emby.media/
.. _hermes: https://github.com/tunnelshade/hermes
