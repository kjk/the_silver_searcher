-- to generate Visual Studio files in vs-premake directory, run:
-- premake4 vs2010 or premake4 vs2008

-- common settings for solutions
function solution_common()
  configurations { "Debug", "Release", "ReleaseKjk" }
  location "vs-premake" -- this is where generated solution/project files go

  -- Symbols - generate .pdb files
  -- StaticRuntime - statically link crt
  -- ExtraWarnings - set max compiler warnings level
  -- FatalWarnings - compiler warnigs are errors'
  -- NoMinimalRebuild - disable /Gm because it clashes with /MP
  flags {
   "Symbols", "StaticRuntime",
   "NoRTTI", "Unicode", "NoExceptions", "NoMinimalRebuild"
  }

  configuration "Debug"
    targetdir "dbg" -- this is where the .exe/.lib etc. files wil end up
    defines { "_DEBUG", "DEBUG" }

  configuration "Release"
     targetdir "rel"
     flags { "Optimize" }
     defines { "NDEBUG" }

  configuration "ReleaseKjk"
     targetdir "rel"
     flags { "Optimize" }
     defines { "NDEBUG", "KJK_BUILD" }

  configuration {"vs*"}
    defines { "_WIN32", "WIN32", "WINDOWS", "_CRT_SECURE_NO_WARNINGS" }

    buildoptions {
        "/wd4800", -- 4800 - int -> bool coversion
        "/wd4127", -- 4127 - conditional expression is constant
        "/wd4100", -- 4100 - unreferenced formal parameter
        "/wd4244", -- 4244 - possible loss of data due to conversion
    }
end

solution "ag"
  solution_common()

  project "ag"
    kind "ConsoleApp"
    language "C++"
    files {
      "src/*.h",
      "src/*.c",
      "wincompat/dirent.*",
      "wincompat/getopt.*",
      "wincompat/unistd.*",
      "wincompat/kjk_crash_handler.*",
    }

    configuration {"vs*"}
      -- /TP  - compile as c++
      buildoptions { "/TP" }

    defines { "PCRE_STATIC", "PTW32_STATIC_LIB" }
    includedirs { "src", "wincompat", "wincompat/zlib", "wincompat/pcre",
    "wincompat/pthread" }
    linkoptions {"/NODEFAULTLIB:\"msvcrt.lib\""}
    links { "Shlwapi", "zlib", "pthread-win32", "pcre" }

  project "pcre"
    kind "StaticLib"
    language "C"
    defines { "HAVE_CONFIG_H" }
    configuration {"vs*"}
      buildoptions {
          "/wd4018", -- signed/unsigned mismatch
          "/wd4146", -- unary minus applied to unsigned type
      }

        files {
      "wincompat/pcre/pcre_byte_order.c",
      "wincompat/pcre/pcre_chartables.c",
      "wincompat/pcre/pcre_compile.c",
      "wincompat/pcre/pcre_config.c",
      "wincompat/pcre/pcre_dfa_exec.c",
      "wincompat/pcre/pcre_exec.c",
      "wincompat/pcre/pcre_fullinfo.c",
      "wincompat/pcre/pcre_get.c",
      "wincompat/pcre/pcre_globals.c",
      "wincompat/pcre/pcre_jit_compile.c",
      "wincompat/pcre/pcre_maketables.c",
      "wincompat/pcre/pcre_newline.c",
      "wincompat/pcre/pcre_ord2utf8.c",
      "wincompat/pcre/pcre_refcount.c",
      "wincompat/pcre/pcre_string_utils.c",
      "wincompat/pcre/pcre_study.c",
      "wincompat/pcre/pcre_tables.c",
      "wincompat/pcre/pcre_ucd.c",
      "wincompat/pcre/pcre_valid_utf8.c",
      "wincompat/pcre/pcre_version.c",
      "wincompat/pcre/pcre_xclass.c",
    }
    includedirs { "wincompat/pcre" }

  project "zlib"
     kind "StaticLib"
     language "C"
     files { "wincompat/zlib/*.c", "wincompat/zlib/*.h" }
     excludes { "wincompat/zlib/gzclose.c", "wincompat/zlib/gzread.c", "wincompat/zlib/gzwrite.c", "wincompat/zlib/gzlib.c"}
     includedirs { "wincompat/zlib" }
     defines { "Z_SOLO" }

  project "pthread-win32"
     kind "StaticLib"
     language "C"
     files {
        "wincompat/pthread/*.h",
        "wincompat/pthread/pthread.c"
     }
     includedirs { "wincompat/pthread" }
     defines { 'PTW32_BUILD_INLINED', 'PTW32_STATIC_LIB', '__CLEANUP_C',
}
