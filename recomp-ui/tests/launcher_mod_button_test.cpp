/* Real Dear ImGui widgets without a platform backend or window. Hover metadata
 * is supplied directly to the unit fixture: no OS input/events or pointer moves. */
#include "backends/imgui/launcher_mod_button.h"
#include "imgui_internal.h"
#include <cassert>
#include <cstdio>
#include <cstring>

static unsigned draw_case(bool enabled, bool hovered) {
    ImGui::NewFrame();
    ImGui::Begin("button-fixture");
    ImGuiContext& g = *GImGui;
    ImDrawList* draw = ImGui::GetWindowDrawList();
    int start = draw->VtxBuffer.Size;
    assert(!rui_mods_button(enabled, "Mods", ImVec2(110, 34)));
    assert(((g.LastItemData.ItemFlags & ImGuiItemFlags_Disabled) != 0) == !enabled);
    unsigned alpha = 0;
    for (int i = start; i < draw->VtxBuffer.Size; ++i) {
        unsigned a = (draw->VtxBuffer[i].col >> IM_COL32_A_SHIFT) & 255;
        if (a > alpha) alpha = a;
    }
    assert(alpha > 0); // The disabled button remains visible.
    assert(!(g.CurrentItemFlags & ImGuiItemFlags_Disabled)); // Other controls unaffected.
    assert(!rui_mods_button_tooltip(enabled)); // No hover -> no message.
    if (hovered) {
        g.LastItemData.StatusFlags |= ImGuiItemStatusFlags_HoveredRect |
                                      ImGuiItemStatusFlags_HoveredWindow;
        if (!enabled) assert(!ImGui::IsItemHovered()); // Ordinary hover rejects disabled widgets.
        ImGui::LogToBuffer();
        assert(rui_mods_button_tooltip(enabled) == !enabled);
        if (!enabled)
            assert(std::strstr(g.LogBuffer.c_str(), "Please select a valid game disc first."));
        else
            assert(!std::strstr(g.LogBuffer.c_str(), "Please select a valid game disc first."));
        ImGui::LogFinish();
    }
    ImGui::End();
    ImGui::Render();
    return alpha;
}

int main() {
    IMGUI_CHECKVERSION(); ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO(); io.IniFilename = nullptr;
    io.DisplaySize = ImVec2(1280, 720); io.DeltaTime = 1.0f / 60.0f;
    unsigned char* pixels; int w, h; io.Fonts->GetTexDataAsRGBA32(&pixels, &w, &h);
    draw_case(false, false); // First-frame window layout.
    const unsigned disabled = draw_case(false, true);
    const unsigned enabled = draw_case(true, true);
    assert(disabled < enabled); // Real disabled styling, not just a click guard.
    ImGui::DestroyContext();
    std::puts("PASS real ImGui Mods button: visible/disabled styling, exact disabled-hover tooltip, enabled state, balanced scope; no desktop/input automation");
}
