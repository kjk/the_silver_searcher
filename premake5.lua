-- to generate Visual Studio files in vs-premake directory, run:
-- premake4 vs2010 or premake4 vs2008

solution 'ag'
    configurations { 'Debug', 'Release', 'ReleaseKjk' }
    location 'vs-premake5' -- this is where generated solution/project files go
    flags { 'StaticRuntime', 'NoRTTI', 'Unicode', 'NoExceptions', }
    defines {
        -- windows
        'WIN32', '_WIN32', 'WINDOWS', '_WINDOWS',
        -- pthread
        'PTW32_BUILD_INLINED', 'PTW32_STATIC_LIB', '__CLEANUP_C',
        -- pcre
        'HAVE_CONFIG_H', 'PCRE_STATIC',
        -- zlib
        'Z_SOLO',
    }

    filter 'action:vs*'
        flags { 'NoMinimalRebuild', 'MultiProcessorCompile', }
        disablewarnings {
            '4996', -- 4996 - same as define _CRT_SECURE_NO_WARNINGS
            '4800', -- 4800 - int -> bool coversion
            '4127', -- 4127 - conditional expression is constant
            '4100', -- 4100 - unreferenced formal parameter
            '4244', -- 4244 - possible loss of data due to conversion
        }
        forceincludes 'pch.h'
        pchheader 'pch.h'
        pchsource 'wincompat/pch.c'

    filter 'configurations:Debug'
        flags { 'Symbols' }
        targetdir 'dbg'
        defines { '_DEBUG', 'DEBUG' }
        optimize 'Debug'

    filter 'configurations:Release*'
        targetdir 'rel'
        defines { 'NDEBUG' }
        optimize 'Full'

project 'ag'
    uuid '066DD594-55FF-4E6C-9DB7-A68131864C7B'
    kind 'ConsoleApp'
    language 'C++'

    includedirs {
        'src',
        'wincompat',
        'wincompat/pcre',
        'wincompat/pthread',
        'wincompat/zlib',
    }
    links {
        'shlwapi',
        'dependlib',
    }
    files {
        'src/**.h',
        'src/**.c',
        'wincompat/*.h',
        'wincompat/*.c',
    }

    filter 'configurations:ReleaseKjk'
        defines { 'KJK_BUILD' }
        files 'wincompat/kjk_crash_handler.cpp'

    filter 'action:not vs*'
        removefiles 'wincompat/pch.h'
        removefiles 'wincompat/pch.c'

    filter 'action:vs*'
        buildoptions '/TP' -- /TP  - compile as c++

project 'dependlib'
    uuid 'D5FE0DC7-F69E-408B-809A-B01B414F9DDF'
    kind 'StaticLib'
    language 'C'

    includedirs {
        'wincompat/pcre',
        'wincompat/pthread',
        'wincompat/zlib',
    }
    files {
        'wincompat/zlib/*.h',
        'wincompat/zlib/*.c',
        'wincompat/pcre/*.h',
        'wincompat/pcre/*.c',
        'wincompat/pthread/*.h',
        'wincompat/pthread/pthread.c',
    }

    filter 'action:vs*'
        files {
            'wincompat/pch.h',
            'wincompat/pch.c',
        }
