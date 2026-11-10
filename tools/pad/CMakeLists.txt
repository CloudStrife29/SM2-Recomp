# EnterElectro-Recomp 0.12 - sm2_pad: controller e tastiera per il riquadro "Comandi" del launcher, con la SDL3 statica del
# toolchain (la stessa del gioco). Lo compila il launcher; SDL3_DIR viene dal toolchain portatile.
cmake_minimum_required(VERSION 3.20)
project(sm2_pad C)
find_package(SDL3 3.2 REQUIRED CONFIG COMPONENTS SDL3-static)
add_executable(sm2_pad sm2_pad.c)
target_link_libraries(sm2_pad PRIVATE SDL3::SDL3-static)
if(MINGW)
  target_link_options(sm2_pad PRIVATE -static)
endif()
