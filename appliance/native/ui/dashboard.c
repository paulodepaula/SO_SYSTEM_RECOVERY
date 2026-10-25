/* RedeTI Recovery OS — Visual MVP v0.6.0
 * Direct DRM/KMS + LVGL 9.6; offline, no desktop or HTTP.
 * Visual reference: appliance/design/DASHBOARD_VISUAL_SPEC_V1.md.
 * Original icon rasters and user-supplied hero laptop are embedded offline
 * in the native ELF. The starfield remains lightweight LVGL primitives.
 */
#include "dashboard.h"
#include "theme.h"
#include "assets.h"
/* Build identity must always come from CMake: fail instead of showing unknown. */
#if !defined(REDETI_BUILD_REV) || !defined(REDETI_APP_VERSION) || !defined(REDETI_BUILD_TAG)
#error "RedeTI build identity was not provided by CMake"
#endif
#include "../input.h"
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

extern const lv_image_dsc_t redeti_pd_logo;

enum {
    C_BG=0x001126, C_HEADER=0x001735, C_SIDE=0x081a2e,
    C_HERO=0x011a38, C_PANEL=0x0a2135, C_CARD=0x1a3049,
    C_ACTIVE=0x054d8e, C_BLUE=0x008cf4, C_CYAN=0x59b2ea,
    C_MINT=0x0fd2b5, C_PURPLE=0xa369f9, C_AMBER=0xf8b935,
    C_WHITE=0xeaf4ff, C_MUTED=0xa5bed8, C_BORDER=0x234761
};

static lv_group_t *s_group;
static lv_obj_t *s_notice;
static lv_obj_t *s_lan;
static lv_obj_t *s_ssh;
static lv_obj_t *s_vpn;
static lv_obj_t *s_status_lan;
static lv_obj_t *s_status_lan_detail;
static lv_obj_t *s_status_lan_dot;
static lv_obj_t *s_status_ssh;
static lv_obj_t *s_status_ssh_detail;
static lv_obj_t *s_status_ssh_dot;
static lv_obj_t *s_status_vpn;
static lv_obj_t *s_status_vpn_detail;
static lv_obj_t *s_status_vpn_dot;
static lv_obj_t *s_input_state;
static lv_obj_t *s_input_detail;
static lv_obj_t *s_input_dot;
static lv_obj_t *s_details;
static lv_obj_t *s_overview;
static lv_obj_t *s_ssh_diagnostics_panel;
static lv_obj_t *s_ssh_diag_state;
static lv_obj_t *s_ssh_diag_reason;
static lv_obj_t *s_ssh_diag_fingerprint;

static void ascii(char *dst, size_t capacity, const char *source)
{
    size_t i=0, j=0;
    if(!source) source="-";
    while(source[i] && j+2<capacity) {
        unsigned char c=(unsigned char)source[i];
        if(c<128) dst[j++]=(char)c, i++;
        else if(c==0xc3 && source[i+1]) {
            unsigned char v=(unsigned char)source[i+1];
            char out='?';
            if(v>=0x80 && v<=0x86) out='A';
            else if(v==0x87) out='C';
            else if(v>=0x88 && v<=0x8b) out='E';
            else if(v>=0x8c && v<=0x8f) out='I';
            else if(v==0x91) out='N';
            else if(v>=0x92 && v<=0x98) out='O';
            else if(v>=0x99 && v<=0x9c) out='U';
            else if(v>=0xa0 && v<=0xa6) out='a';
            else if(v==0xa7) out='c';
            else if(v>=0xa8 && v<=0xab) out='e';
            else if(v>=0xac && v<=0xaf) out='i';
            else if(v==0xb1) out='n';
            else if(v>=0xb2 && v<=0xb8) out='o';
            else if(v>=0xb9 && v<=0xbc) out='u';
            dst[j++]=out; i+=2;
        } else {
            dst[j++]='?'; i++;
            while(source[i] && ((unsigned char)source[i]&0xc0)==0x80) i++;
        }
    }
    dst[j]=0;
}
static void set_text(lv_obj_t *label, const char *text)
{
    char buf[640];
    ascii(buf,sizeof buf,text);
    lv_label_set_text(label,buf);
}
static void bg(lv_obj_t *obj, uint32_t color, int radius, int border)
{
    lv_obj_set_style_bg_opa(obj,LV_OPA_COVER,0);
    lv_obj_set_style_bg_color(obj,lv_color_hex(color),0);
    lv_obj_set_style_radius(obj,radius,0);
    lv_obj_set_style_border_width(obj,border,0);
    lv_obj_set_style_border_color(obj,lv_color_hex(C_BORDER),0);
    lv_obj_set_style_pad_all(obj,0,0);
    lv_obj_set_style_shadow_width(obj,0,0);
    lv_obj_set_scrollbar_mode(obj,LV_SCROLLBAR_MODE_OFF);
}
static lv_obj_t *box(lv_obj_t *parent,uint32_t color,int radius,int border)
{
    lv_obj_t *o=lv_obj_create(parent);
    bg(o,color,radius,border);
    return o;
}
static lv_obj_t *txt(lv_obj_t *parent,const char *value,int size,uint32_t color)
{
    lv_obj_t *o=lv_label_create(parent);
    set_text(o,value);
    lv_obj_set_style_text_color(o,lv_color_hex(color),0);
    const lv_font_t *font=&lv_font_montserrat_16;
    if(size<=14) font=&lv_font_montserrat_14;
    else if(size>=28) font=&lv_font_montserrat_28;
    else if(size>=20) font=&lv_font_montserrat_20;
    lv_obj_set_style_text_font(o,font,0);
    lv_label_set_long_mode(o,LV_LABEL_LONG_WRAP);
    return o;
}
/* The same original 24px line language is used across every UI region. */
static const lv_image_dsc_t *icon_source(const char *icon)
{
    if(!icon)return NULL;
#define ICON_FOR(glyph,kind) if(strcmp(icon,glyph)==0)return &redeti_icon_##kind
    ICON_FOR(LV_SYMBOL_HOME,home);
    ICON_FOR(LV_SYMBOL_LIST,list);
    ICON_FOR(LV_SYMBOL_DRIVE,drive);
    ICON_FOR(LV_SYMBOL_CHARGE,charge);
    ICON_FOR(LV_SYMBOL_SETTINGS,settings);
    ICON_FOR(LV_SYMBOL_FILE,file);
    ICON_FOR(LV_SYMBOL_WIFI,wifi);
    ICON_FOR(LV_SYMBOL_IMAGE,image);
    ICON_FOR(LV_SYMBOL_EYE_OPEN,eye);
    ICON_FOR(LV_SYMBOL_POWER,power);
    ICON_FOR(LV_SYMBOL_REFRESH,refresh);
    ICON_FOR(LV_SYMBOL_PLAY,play);
    ICON_FOR(LV_SYMBOL_KEYBOARD,keyboard);
    ICON_FOR(LV_SYMBOL_DOWNLOAD,download);
    ICON_FOR(LV_SYMBOL_DIRECTORY,directory);
    ICON_FOR(LV_SYMBOL_SAVE,save);
    ICON_FOR(LV_SYMBOL_OK,ok);
#undef ICON_FOR
    return NULL;
}
static lv_obj_t *symbol(lv_obj_t *parent,const char *icon,uint32_t color,int size)
{
    const lv_image_dsc_t *src=icon_source(icon);
    if(src) {
        lv_obj_t *image=lv_image_create(parent);
        lv_image_set_src(image,src);
        /* One white raster icon, tinted per context via LVGL style. */
        lv_obj_set_style_image_recolor(image,lv_color_hex(color),0);
        lv_obj_set_style_image_recolor_opa(image,LV_OPA_COVER,0);
        (void)size;
        return image;
    }
    /* Safe font fallback for any symbol added in future code. */
    lv_obj_t *o=lv_label_create(parent);
    lv_label_set_text(o,icon);
    lv_obj_set_style_text_font(o,size>=28?&lv_font_montserrat_28:&lv_font_montserrat_20,0);
    lv_obj_set_style_text_color(o,lv_color_hex(color),0);
    return o;
}
static lv_obj_t *badge_icon(lv_obj_t *parent,const char *icon,uint32_t color)
{
    lv_obj_t *b=box(parent,0x0a3454,10,1);
    lv_obj_set_size(b,46,46);
    lv_obj_set_style_border_color(b,lv_color_hex(color),0);
    redeti_theme_gradient(b,0x0b3a5b,0x061e3a);
    lv_obj_t *s=symbol(b,icon,color,25);
    lv_obj_center(s);
    return b;
}
static void flex(lv_obj_t *obj,lv_flex_flow_t flow,int gap)
{
    lv_obj_set_flex_flow(obj,flow);
    lv_obj_set_style_pad_row(obj,gap,0);
    lv_obj_set_style_pad_column(obj,gap,0);
}
static json_object *value(json_object *root,const char *key)
{
    json_object *v=NULL;
    if(root)json_object_object_get_ex(root,key,&v);
    return v;
}
static const char *str(json_object *root,const char *key)
{
    json_object *v=value(root,key);
    return v&&json_object_is_type(v,json_type_string)?json_object_get_string(v):"-";
}
static void set_notice(const char *message)
{
    if(s_notice)set_text(s_notice,message);
}
static void clicked_test(lv_event_t *e)
{
    (void)e;
    set_notice("Entrada OK: clique ou Enter recebido. Mouse e teclado funcionando.");
}
static void clicked_details(lv_event_t *e)
{
    (void)e;
    set_notice("Inventario inicial apresentado; nenhuma operacao de reparo executada.");
    if(s_details)lv_obj_scroll_to_view(s_details,LV_ANIM_ON);
}
static void clicked_home(lv_event_t *e)
{
    (void)e;
    if(s_overview)lv_obj_scroll_to_y(s_overview,0,LV_ANIM_ON);
}
static void clicked_network(lv_event_t *e)
{
    (void)e;
    set_notice("Rede/SSH: diagnostico seguro disponivel abaixo do inventario.");
    if(s_ssh_diagnostics_panel)lv_obj_scroll_to_view(s_ssh_diagnostics_panel,LV_ANIM_ON);
    else if(s_status_lan)lv_obj_scroll_to_view(s_status_lan,LV_ANIM_ON);
}
static void style_button(lv_obj_t *b,uint32_t base)
{
    bg(b,base,10,1);
    redeti_theme_gradient(b,base,base==C_ACTIVE?0x063568:0x091c30);
    lv_obj_set_style_border_color(b,lv_color_hex(0x1c72ac),0);
    lv_obj_set_style_outline_color(b,lv_color_hex(C_CYAN),LV_STATE_FOCUSED);
    lv_obj_set_style_outline_width(b,2,LV_STATE_FOCUSED);
    lv_obj_set_style_outline_pad(b,2,LV_STATE_FOCUSED);
    lv_obj_set_style_bg_color(b,lv_color_hex(0x0562ad),LV_STATE_PRESSED);
}
static lv_obj_t *button(lv_obj_t *parent,const char *caption,const char *glyph,
                         int width,lv_event_cb_t cb)
{
    lv_obj_t *b=lv_button_create(parent);
    lv_obj_set_size(b,width,52);
    style_button(b,cb?C_ACTIVE:0x10293f);
    lv_obj_set_style_pad_left(b,16,0);
    lv_obj_set_style_pad_right(b,16,0);
    flex(b,LV_FLEX_FLOW_ROW,10);
    lv_obj_set_flex_align(b,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER);
    if(glyph)symbol(b,glyph,C_WHITE,20);
    txt(b,caption,16,cb?C_WHITE:C_MUTED);
    if(cb) {
        lv_obj_add_event_cb(b,cb,LV_EVENT_CLICKED,NULL);
        if(s_group)lv_group_add_obj(s_group,b);
    } else {
        /* Keep pending actions visibly secondary without LVGL's grey fill. */
        lv_obj_add_state(b,LV_STATE_DISABLED);
        lv_obj_set_style_bg_color(b,lv_color_hex(0x10293f),LV_STATE_DISABLED);
        lv_obj_set_style_bg_opa(b,LV_OPA_COVER,LV_STATE_DISABLED);
        lv_obj_set_style_border_color(b,lv_color_hex(C_BORDER),LV_STATE_DISABLED);
        lv_obj_set_style_opa(b,LV_OPA_COVER,LV_STATE_DISABLED);
    }
    return b;
}
/* Six equal action cards, 3 columns x 2 rows at desktop widths.
 * Reuses the existing callbacks, no new diagnostics or repair operations. */
static lv_obj_t *quick_action_tile(lv_obj_t *parent,const char *caption,
                                   const char *glyph,int width,lv_event_cb_t cb)
{
    bool available=cb!=NULL;
    lv_obj_t *tile=lv_button_create(parent);
    lv_obj_set_size(tile,width,69);
    style_button(tile,available?0x0e3456:0x0b2339);
    redeti_theme_quick_tile(tile,available);
    lv_obj_set_style_pad_left(tile,10,0);
    lv_obj_set_style_pad_right(tile,8,0);
    lv_obj_set_style_pad_top(tile,7,0);
    lv_obj_set_style_pad_bottom(tile,7,0);
    flex(tile,LV_FLEX_FLOW_ROW,8);
    lv_obj_set_flex_align(tile,LV_FLEX_ALIGN_START,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER);
    symbol(tile,glyph,available?C_CYAN:C_MUTED,20);
    lv_obj_t *label=txt(tile,caption,14,available?C_WHITE:C_MUTED);
    lv_obj_set_width(label,width-10-8-24-8);
    lv_label_set_long_mode(label,LV_LABEL_LONG_WRAP);
    lv_obj_set_style_text_line_space(label,2,0);
    if(available) {
        lv_obj_add_event_cb(tile,cb,LV_EVENT_CLICKED,NULL);
        if(s_group)lv_group_add_obj(s_group,tile);
    } else {
        lv_obj_add_state(tile,LV_STATE_DISABLED);
    }
    return tile;
}

static lv_obj_t *status_chip(lv_obj_t *parent,const char *glyph,const char *caption,lv_obj_t **result,int width)
{
    lv_obj_t *chip=box(parent,0x061b31,10,1);
    lv_obj_set_size(chip,width,64);
    redeti_theme_card(chip,0x082b49,0x05182f);
    lv_obj_set_style_pad_all(chip,6,0);
    flex(chip,LV_FLEX_FLOW_ROW,8);
    lv_obj_set_flex_align(chip,LV_FLEX_ALIGN_START,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_START);
    badge_icon(chip,glyph,C_CYAN);
    lv_obj_t *textcol=box(chip,0x061b31,0,0);
    flex(textcol,LV_FLEX_FLOW_COLUMN,1);
    lv_obj_set_style_bg_opa(textcol,LV_OPA_TRANSP,0);
    lv_obj_set_size(textcol,width-68,50);
    txt(textcol,caption,14,C_CYAN);
    *result=txt(textcol,"Aguardando...",14,C_WHITE);
    lv_obj_set_width(*result,lv_pct(100));
    return chip;
}
/* Read only the PUBLIC server fingerprint from tmpfs, never host private keys. */
static const char *ssh_key_reason(const char *token)
{
    if(strcmp(token,"installed")==0)return "Chave Ed25519 carregada do pendrive";
    if(strcmp(token,"waiting_usb")==0)return "USB nao encontrado: Ventoy/REDETI_CFG em FAT32/exFAT";
    if(strcmp(token,"usb_mount_failed")==0)return "Particao USB detectada, mas leitura falhou";
    if(strcmp(token,"key_file_missing")==0)return "Falta REDETI/authorized_keys na particao USB";
    if(strcmp(token,"invalid_public_key")==0)return "Arquivo invalido: exige chave publica ssh-ed25519";
    return "Aguardando provisionamento por pendrive";
}
static void read_ssh_public_fingerprint(char *out,size_t cap)
{
    if(cap==0)return;
    snprintf(out,cap,"Identidade SSH: aguardando chave de servidor");
    FILE *in=fopen("/run/redeti/ssh/host_fingerprint","r");
    if(!in)return;
    char line[256];
    if(fgets(line,sizeof line,in)) {
        const char *start=strstr(line,"SHA256:");
        if(start) {
            size_t n=strcspn(start," \t\r\n");
            if(n>7 && n<90)snprintf(out,cap,"Identidade SSH: %.*s",(int)n,start);
        }
    }
    fclose(in);
}
/* A coloured dot signals a measured state, never a mocked connection. */
static void status_indicator(lv_obj_t *dot,uint32_t color)
{
    if(dot)lv_obj_set_style_bg_color(dot,lv_color_hex(color),0);
}
static void update_connections(lv_timer_t *timer)
{
    (void)timer;
    json_object *lan=json_object_from_file("/run/redeti/lan-ssh-status.json");
    json_object *vpn=json_object_from_file("/run/redeti/remote-status.json");
    const char *lan_state=str(lan,"state");
    const char *ip=str(lan,"lan_ip");
    const char *vpn_state=str(vpn,"state");
    bool have_lan=strcmp(lan_state,"ready")==0||strcmp(lan_state,"awaiting_key")==0;
    if(s_lan)set_text(s_lan,have_lan?ip:"Sem rede");
    if(s_ssh) {
        char address[80];
        snprintf(address,sizeof address,"paulo@%s",ip);
        set_text(s_ssh,strcmp(lan_state,"ready")==0?address:
                    have_lan?"Aguardando chave":"Sem rede");
    }
    if(s_vpn)set_text(s_vpn,strcmp(vpn_state,"connected")==0?"Online":
                           strcmp(vpn_state,"connecting")==0?"Conectando":"Sem VPN");
    /* Four rows, three columns: source | verified state | detail. */
    bool ssh_ready=strcmp(lan_state,"ready")==0;
    bool vpn_ready=strcmp(vpn_state,"connected")==0;
    bool vpn_connecting=strcmp(vpn_state,"connecting")==0;
    if(s_status_lan)set_text(s_status_lan,have_lan?"Conectada (LAN)":"Sem rede");
    if(s_status_lan_detail)set_text(s_status_lan_detail,have_lan?ip:"-");
    status_indicator(s_status_lan_dot,have_lan?C_MINT:0x7894ad);

    if(s_status_ssh)set_text(s_status_ssh,ssh_ready?"Protegido":
                             have_lan?"Aguardando chave":"Sem rede");
    if(s_status_ssh_detail)set_text(s_status_ssh_detail,ssh_ready?"usuario: paulo":
                                    have_lan?"Sem chave":"-");
    status_indicator(s_status_ssh_dot,ssh_ready?C_MINT:
                     have_lan?C_AMBER:0x7894ad);

    if(s_status_vpn)set_text(s_status_vpn,vpn_ready?"Conectada":
                             vpn_connecting?"Conectando":"Nao provisionada");
    if(s_status_vpn_detail)set_text(s_status_vpn_detail,vpn_ready?str(vpn,"vpn_ip"):"-");
    status_indicator(s_status_vpn_dot,vpn_ready?C_MINT:
                     vpn_connecting?C_AMBER:0x7894ad);
    if(s_ssh_diag_state) {
        char summary[180];
        snprintf(summary,sizeof summary,"LAN: %s | SSH: %s | usuario: paulo",
                 have_lan?ip:"indisponivel",lan_state);
        set_text(s_ssh_diag_state,summary);
    }
    if(s_ssh_diag_reason)set_text(s_ssh_diag_reason,ssh_key_reason(str(lan,"key_reason")));
    if(s_ssh_diag_fingerprint) {
        char fingerprint[160];
        read_ssh_public_fingerprint(fingerprint,sizeof fingerprint);
        set_text(s_ssh_diag_fingerprint,fingerprint);
    }
    if(lan)json_object_put(lan);
    if(vpn)json_object_put(vpn);
}
static void stars(lv_obj_t *parent,int width,int height)
{
    for(int i=0;i<31;i++) {
        int x=(i*83+47)%width;
        int y=(i*53+19)%height;
        lv_obj_t *star=box(parent,(i%5==0)?0x227ab0:0x12405f,LV_RADIUS_CIRCLE,0);
        lv_obj_set_size(star,i%6==0?3:2,i%6==0?3:2);
        lv_obj_set_floating(star,true);
        lv_obj_set_pos(star,x,y);
    }
}
static void laptop_art(lv_obj_t *parent,int width)
{
    /* User-provided transparent 380x197 laptop, embedded in the native ELF.
     * Keep the artwork inside its right-hand hero column. */
    lv_obj_t *scene=box(parent,C_HERO,0,0);
    lv_obj_set_style_bg_opa(scene,LV_OPA_TRANSP,0);
    lv_obj_set_size(scene,width,197);
    lv_obj_remove_flag(scene,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t *illustration=lv_image_create(scene);
    lv_image_set_src(illustration,&redeti_hero_laptop);
    uint32_t scale=(uint32_t)((width-12)*256U/380U);
    if(scale>256U)scale=256U;
    lv_image_set_scale(illustration,scale);
    lv_obj_center(illustration);
}
static void header(lv_obj_t *root,int width)
{
    lv_obj_t *h=box(root,C_HEADER,0,0);
    lv_obj_set_size(h,width,92);
    redeti_theme_gradient(h,0x052248,0x00132c);
    lv_obj_set_style_pad_left(h,20,0);
    lv_obj_set_style_pad_right(h,20,0);
    flex(h,LV_FLEX_FLOW_ROW,18);
    lv_obj_set_flex_align(h,LV_FLEX_ALIGN_START,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER);
    lv_obj_t *mark=lv_image_create(h);
    lv_image_set_src(mark,&redeti_pd_logo);
    lv_obj_set_size(mark,64,64);
    lv_obj_t *heading=box(h,C_HEADER,0,0);
    lv_obj_set_style_bg_opa(heading,LV_OPA_TRANSP,0);
    lv_obj_set_size(heading,width<1500?375:490,70);
    flex(heading,LV_FLEX_FLOW_COLUMN,4);
    txt(heading,"RedeTI Recovery OS",28,C_WHITE);
    txt(heading,"DIAGNOSTICO AUTOMATICO | SOMENTE LEITURA",14,C_CYAN);
    if(width>=1200) {
        lv_obj_t *right=box(h,C_HEADER,0,0);
        lv_obj_set_style_bg_opa(right,LV_OPA_TRANSP,0);
        lv_obj_set_flex_grow(right,1);
        lv_obj_set_height(right,74);
        flex(right,LV_FLEX_FLOW_ROW,8);
        lv_obj_set_flex_align(right,LV_FLEX_ALIGN_END,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_END);
        status_chip(right,LV_SYMBOL_WIFI,"Rede Local",&s_lan,width<1500?152:177);
        status_chip(right,LV_SYMBOL_HOME,"SSH / paulo",&s_ssh,width<1500?158:189);
        status_chip(right,LV_SYMBOL_OK,"VPN",&s_vpn,width<1500?137:166);
        lv_obj_t *ver=box(right,0x062b4c,9,1);
        /* Release, build time (UTC) and source SHA are always visible.
         * Three compact lines identify a unique ISO without consuming
         * a whole header row on 1280/1366 desktop modes. */
        lv_obj_set_size(ver,140,70);
        flex(ver,LV_FLEX_FLOW_COLUMN,1);
        lv_obj_set_style_pad_all(ver,5,0);
        txt(ver,REDETI_APP_VERSION,16,C_WHITE);
        txt(ver,REDETI_BUILD_TAG,14,C_CYAN);
        txt(ver,REDETI_BUILD_REV,14,C_MUTED);
    }
}
static void nav_item(lv_obj_t *side,const char *name,const char *glyph,
                     bool active,bool compact,lv_event_cb_t cb)
{
    lv_obj_t *b=lv_button_create(side);
    lv_obj_set_width(b,lv_pct(100));
    lv_obj_set_height(b,46);
    style_button(b,active?C_ACTIVE:C_SIDE);
    if(active)redeti_theme_active(b);
    if(!active)lv_obj_set_style_border_width(b,0,0);
    lv_obj_set_style_pad_left(b,10,0);
    lv_obj_set_style_pad_right(b,10,0);
    flex(b,LV_FLEX_FLOW_ROW,12);
    lv_obj_set_flex_align(b,LV_FLEX_ALIGN_START,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER);
    symbol(b,glyph,active?C_CYAN:C_MUTED,20);
    if(!compact)txt(b,name,14,active?C_WHITE:C_MUTED);
    if(cb) {
        lv_obj_add_event_cb(b,cb,LV_EVENT_CLICKED,NULL);
        if(s_group)lv_group_add_obj(s_group,b);
    } else {
        /* Keep unimplemented nav entries subtle, not solid grey buttons. */
        lv_obj_remove_flag(b,LV_OBJ_FLAG_CLICKABLE);
    }
}
static void sidebar(lv_obj_t *side,bool compact)
{
    lv_obj_set_style_pad_all(side,10,0);
    redeti_theme_gradient(side,0x0b263e,0x061427);
    flex(side,LV_FLEX_FLOW_COLUMN,7);
    nav_item(side,"Inicio",LV_SYMBOL_HOME,true,compact,clicked_home);
    nav_item(side,"Diagnostico",LV_SYMBOL_LIST,false,compact,clicked_details);
    nav_item(side,"Discos e Particoes",LV_SYMBOL_DRIVE,false,compact,clicked_details);
    nav_item(side,"SMART",LV_SYMBOL_CHARGE,false,compact,NULL);
    nav_item(side,"EFI / BCD",LV_SYMBOL_SETTINGS,false,compact,NULL);
    nav_item(side,"Windows",LV_SYMBOL_FILE,false,compact,NULL);
    nav_item(side,"Rede",LV_SYMBOL_WIFI,false,compact,clicked_network);
    nav_item(side,"Hardware",LV_SYMBOL_IMAGE,false,compact,clicked_details);
    nav_item(side,"Logs",LV_SYMBOL_FILE,false,compact,NULL);
    nav_item(side,"Configuracoes",LV_SYMBOL_SETTINGS,false,compact,NULL);
    nav_item(side,"Sobre",LV_SYMBOL_EYE_OPEN,false,compact,NULL);
    nav_item(side,"Desligar",LV_SYMBOL_POWER,false,compact,NULL);
}
static void hero(lv_obj_t *content,int width,bool notebook)
{
    /* Fit the laptop even at 1280-wide DRM resolutions (content ~1018px). */
    int laptop_width=notebook?(width>=1180?420:width>=960?340:275):0;
    int left_width=width-laptop_width-56;
    lv_obj_t *area=box(content,C_HERO,16,1);
    lv_obj_set_width(area,lv_pct(100));
    lv_obj_set_height(area,245);
    lv_obj_set_style_border_color(area,lv_color_hex(0x09598e),0);
    redeti_theme_gradient(area,0x0a3260,0x01172f);
    redeti_theme_glow(area,0x008ce8,38);
    lv_obj_set_style_pad_all(area,22,0);
    flex(area,LV_FLEX_FLOW_ROW,12);
    stars(area,width,240);
    lv_obj_t *left=box(area,C_HERO,0,0);
    lv_obj_set_style_bg_opa(left,LV_OPA_TRANSP,0);
    lv_obj_set_size(left,left_width,205);
    flex(left,LV_FLEX_FLOW_COLUMN,9);
    txt(left,"Diagnostico Automatico",28,C_WHITE);
    txt(left,"Verificacao rapida de hardware, disco, sistema e rede.",14,C_MUTED);
    lv_obj_t *reasons=box(left,C_HERO,0,0);
    lv_obj_set_style_bg_opa(reasons,LV_OPA_TRANSP,0);
    lv_obj_set_size(reasons,lv_pct(100),47);
    flex(reasons,LV_FLEX_FLOW_ROW,18);
    txt(reasons,"[+] Somente leitura",14,C_CYAN);
    txt(reasons,"[+] Seguro",14,C_MINT);
    txt(reasons,"[+] Rapido",14,C_AMBER);
    lv_obj_t *actions=box(left,C_HERO,0,0);
    lv_obj_set_style_bg_opa(actions,LV_OPA_TRANSP,0);
    lv_obj_set_size(actions,lv_pct(100),55);
    flex(actions,LV_FLEX_FLOW_ROW,10);
    lv_obj_t *start=button(actions,"VER DIAGNOSTICO",LV_SYMBOL_PLAY,notebook?256:230,clicked_details);
    lv_obj_set_style_bg_color(start,lv_color_hex(C_BLUE),0);
    button(actions,"TESTAR ENTRADA",LV_SYMBOL_KEYBOARD,notebook?221:214,clicked_test);
    if(notebook)laptop_art(area,laptop_width);
}
static void data_card(lv_obj_t *row,int width,const char *glyph,uint32_t tint,
                      const char *name,const char *val,const char *foot)
{
    lv_obj_t *card=box(row,C_CARD,14,1);
    lv_obj_set_size(card,width,147);
    lv_obj_set_style_pad_all(card,16,0);
    redeti_theme_card(card,0x1b3955,0x0d233a);
    flex(card,LV_FLEX_FLOW_COLUMN,6);
    lv_obj_t *r=box(card,C_CARD,0,0);
    lv_obj_set_style_bg_opa(r,LV_OPA_TRANSP,0);
    lv_obj_set_size(r,lv_pct(100),42);
    flex(r,LV_FLEX_FLOW_ROW,12);
    badge_icon(r,glyph,tint);
    lv_obj_t *sub=box(r,C_CARD,0,0);
    lv_obj_set_style_bg_opa(sub,LV_OPA_TRANSP,0);
    lv_obj_set_flex_grow(sub,1);
    lv_obj_set_height(sub,42);
    txt(sub,name,14,C_MUTED);
    lv_obj_t *v=txt(card,val,16,C_WHITE);
    lv_obj_set_width(v,lv_pct(100));
    if(foot)txt(card,foot,14,C_MUTED);
}
/* Three aligned columns, matching the approved status reference.
 * Left: icon and subsystem; centre: coloured dot and real state;
 * right: contextual value aligned to the right. No mock addresses. */
static void status_row3(lv_obj_t *parent,int row_width,const char *glyph,
                        const char *title,lv_obj_t **state,
                        lv_obj_t **detail,lv_obj_t **indicator)
{
    const int label_w=row_width<480?100:112;
    const int detail_w=row_width<480?104:130;
    const int centre_w=row_width-20-18-label_w-detail_w;
    lv_obj_t *row=box(parent,0x0b2742,7,0);
    lv_obj_set_size(row,lv_pct(100),39);
    redeti_theme_gradient(row,0x102e49,0x0b233b);
    lv_obj_set_style_pad_left(row,10,0);
    lv_obj_set_style_pad_right(row,10,0);
    flex(row,LV_FLEX_FLOW_ROW,9);
    lv_obj_set_flex_align(row,LV_FLEX_ALIGN_START,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER);

    lv_obj_t *left=box(row,C_PANEL,0,0);
    lv_obj_set_style_bg_opa(left,LV_OPA_TRANSP,0);
    lv_obj_set_size(left,label_w,27);
    flex(left,LV_FLEX_FLOW_ROW,7);
    lv_obj_set_flex_align(left,LV_FLEX_ALIGN_START,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER);
    symbol(left,glyph,C_CYAN,20);
    txt(left,title,14,C_MUTED);

    lv_obj_t *centre=box(row,C_PANEL,0,0);
    lv_obj_set_style_bg_opa(centre,LV_OPA_TRANSP,0);
    lv_obj_set_size(centre,centre_w,27);
    flex(centre,LV_FLEX_FLOW_ROW,9);
    lv_obj_set_flex_align(centre,LV_FLEX_ALIGN_START,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER);
    *indicator=box(centre,0x7894ad,LV_RADIUS_CIRCLE,0);
    lv_obj_set_size(*indicator,10,10);
    *state=txt(centre,"Aguardando",14,C_WHITE);
    lv_obj_set_width(*state,centre_w-19);
    lv_label_set_long_mode(*state,LV_LABEL_LONG_DOT);

    *detail=txt(row,"-",14,C_MUTED);
    lv_obj_set_width(*detail,detail_w);
    lv_label_set_long_mode(*detail,LV_LABEL_LONG_DOT);
    lv_obj_set_style_text_align(*detail,LV_TEXT_ALIGN_RIGHT,0);
}
static lv_obj_t *section(lv_obj_t *parent,const char *title,int height)
{
    lv_obj_t *o=box(parent,C_PANEL,14,1);
    lv_obj_set_height(o,height);
    lv_obj_set_style_pad_all(o,12,0);
    redeti_theme_card(o,0x0e2b46,0x071b30);
    flex(o,LV_FLEX_FLOW_COLUMN,8);
    txt(o,title,16,C_WHITE);
    return o;
}
static void module_item(lv_obj_t *parent,int width,const char *glyph,
                        const char *title,const char *note,bool available)
{
    lv_obj_t *m=box(parent,0x102c46,10,1);
    lv_obj_set_size(m,width,69);
    redeti_theme_gradient(m,0x163651,0x0b273e);
    lv_obj_set_style_pad_all(m,9,0);
    flex(m,LV_FLEX_FLOW_ROW,9);
    lv_obj_set_flex_align(m,LV_FLEX_ALIGN_START,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER);
    badge_icon(m,glyph,available?C_CYAN:C_MUTED);
    lv_obj_t *labels=box(m,0x102c46,0,0);
    lv_obj_set_style_bg_opa(labels,LV_OPA_TRANSP,0);
    lv_obj_set_flex_grow(labels,1);
    lv_obj_set_height(labels,51);
    flex(labels,LV_FLEX_FLOW_COLUMN,4);
    txt(labels,title,14,available?C_WHITE:C_MUTED);
    txt(labels,note,14,C_MUTED);
}
static void inventory(lv_obj_t *content,json_object *hw)
{
    lv_obj_t *sec=section(content,"Discos e Particoes | Inventario somente leitura",200);
    s_details=sec;
    lv_obj_set_width(sec,lv_pct(100));
    json_object *devices=value(hw,"disks");
    size_t n=devices&&json_object_is_type(devices,json_type_array)?
              json_object_array_length(devices):0;
    if(!n){txt(sec,"Nenhum disco detectado. Conecte uma unidade de laboratorio para validar.",16,C_MUTED);return;}
    for(size_t i=0;i<n && i<6;i++){
        json_object *d=json_object_array_get_idx(devices,i);
        char line[300];
        json_object *byteval=value(d,"size_bytes");
        double gb=byteval?json_object_get_double(byteval)/1073741824.:0;
        snprintf(line,sizeof line,"%s | %s | %.1f GiB | %s",
                 str(d,"device"),str(d,"model"),gb,
                 json_object_get_boolean(value(d,"is_removable_or_usb"))?"USB/RECOVERY":"INTERNO");
        txt(sec,line,14,C_CYAN);
        json_object *parts=value(d,"partitions");
        size_t count=parts&&json_object_is_type(parts,json_type_array)?
                         json_object_array_length(parts):0;
        for(size_t j=0;j<count && j<3;j++){
            json_object *p=json_object_array_get_idx(parts,j);
            snprintf(line,sizeof line,"  %s | %s | OS nao confirmado",str(p,"device"),str(p,"filesystem"));
            txt(sec,line,14,C_MUTED);
        }
    }
    lv_obj_set_height(sec,LV_SIZE_CONTENT);
}
void redeti_dashboard_create(lv_display_t *display,json_object *hw)
{
    int sw=lv_display_get_horizontal_resolution(display);
    int sh=lv_display_get_vertical_resolution(display);
    if(sw<640||sh<480){fprintf(stderr,"RedeTI: mode too small for dashboard\n");return;}
    bool compact=sw<1200, legacy=sw<900;
    int sb=legacy?0:(compact?72:(sw>=1500?239:220));
    /* Reserve a dedicated right-hand scroll gutter; cards never sit below the scrollbar. */
    int viewportw=sw-sb-(legacy?0:18)-24;
    int scroll_gutter=20;
    int mainw=viewportw-scroll_gutter;
    int cols=mainw>=860?4:2;
    int cardw=(mainw-12*(cols-1))/cols;
    s_group=lv_group_create();

    lv_obj_t *root=lv_screen_active();
    bg(root,C_BG,0,0);
    lv_obj_set_style_pad_all(root,0,0);
    lv_obj_set_scrollbar_mode(root,LV_SCROLLBAR_MODE_OFF);
    lv_obj_set_scroll_dir(root,LV_DIR_NONE);
    flex(root,LV_FLEX_FLOW_COLUMN,0);
    header(root,sw);
    lv_obj_t *body=box(root,C_BG,0,0);
    lv_obj_set_size(body,sw,sh-92);
    flex(body,LV_FLEX_FLOW_ROW,14);
    lv_obj_set_style_pad_all(body,12,0);
    lv_obj_t *side=NULL;
    if(!legacy) {
        side=box(body,C_SIDE,14,1);
        lv_obj_set_size(side,sb,sh-116);
    }
    lv_obj_t *content=box(body,C_BG,0,0);
    lv_obj_set_size(content,viewportw,sh-116);
    /* Percent-width children now use only mainw; scrollbar owns its gutter. */
    lv_obj_set_style_bg_opa(content,LV_OPA_TRANSP,0);
    lv_obj_set_style_pad_right(content,scroll_gutter,0);
    lv_obj_set_scroll_dir(content,LV_DIR_VER);
    redeti_theme_scrollbar(content);
    flex(content,LV_FLEX_FLOW_COLUMN,12);
    s_overview=content;
    hero(content,mainw,mainw>=900);

    lv_obj_t *stat=box(content,C_BG,0,0);
    lv_obj_set_style_bg_opa(stat,LV_OPA_TRANSP,0);
    lv_obj_set_width(stat,lv_pct(100));
    lv_obj_set_height(stat,cols==4?150:308);
    flex(stat,LV_FLEX_FLOW_ROW_WRAP,12);

    char ram[80];snprintf(ram,sizeof ram,"--");
    json_object *mem=value(hw,"ram_bytes");
    if(mem)snprintf(ram,sizeof ram,"%.1f GiB",json_object_get_double(mem)/1073741824.);
    data_card(stat,cardw,LV_SYMBOL_SETTINGS,C_CYAN,"Processador",str(value(hw,"cpu"),"model"),"CPU identificada");
    data_card(stat,cardw,LV_SYMBOL_CHARGE,C_MINT,"Memoria RAM",ram,"Capacidade total");
    data_card(stat,cardw,LV_SYMBOL_REFRESH,C_PURPLE,"Modo de inicializacao",
             str(hw,"recovery_boot_firmware"),"Boot deste Recovery OS");
    const char *target=str(value(hw,"target"),"message");
    data_card(stat,cardw,LV_SYMBOL_DRIVE,C_AMBER,"Disco e Windows",target,"Windows requer verificacao");

    lv_obj_t *mid=box(content,C_BG,0,0);
    lv_obj_set_style_bg_opa(mid,LV_OPA_TRANSP,0);
    const int panel_height=222;
    bool stack_mid=mainw<900;
    lv_obj_set_size(mid,lv_pct(100),stack_mid?panel_height*2+12:panel_height);
    flex(mid,stack_mid?LV_FLEX_FLOW_COLUMN:LV_FLEX_FLOW_ROW,12);
    int half=stack_mid?mainw:(mainw-12)/2;
    lv_obj_t *system=section(mid,"Status do Sistema",panel_height);
    lv_obj_set_width(system,half);
    lv_obj_t *statusgrid=box(system,C_PANEL,0,0);
    lv_obj_set_style_bg_opa(statusgrid,LV_OPA_TRANSP,0);
    lv_obj_set_size(statusgrid,lv_pct(100),164);
    flex(statusgrid,LV_FLEX_FLOW_COLUMN,2);
    const int row_width=half-24;
    status_row3(statusgrid,row_width,LV_SYMBOL_WIFI,"Rede",
                &s_status_lan,&s_status_lan_detail,&s_status_lan_dot);
    status_row3(statusgrid,row_width,LV_SYMBOL_HOME,"SSH",
                &s_status_ssh,&s_status_ssh_detail,&s_status_ssh_dot);
    status_row3(statusgrid,row_width,LV_SYMBOL_OK,"VPN",
                &s_status_vpn,&s_status_vpn_detail,&s_status_vpn_dot);
    status_row3(statusgrid,row_width,LV_SYMBOL_KEYBOARD,"Entrada",
                &s_input_state,&s_input_detail,&s_input_dot);

    lv_obj_t *quick=section(mid,"Acoes Rapidas",panel_height);
    lv_obj_set_width(quick,half);
    lv_obj_t *actions=box(quick,C_PANEL,0,0);
    lv_obj_set_style_bg_opa(actions,LV_OPA_TRANSP,0);
    lv_obj_set_size(actions,lv_pct(100),160);
    flex(actions,LV_FLEX_FLOW_ROW_WRAP,8);
    /* Reference layout: three aligned columns x two rows. */
    int aq=(half-24-16)/3;
    quick_action_tile(actions,"Inventario",LV_SYMBOL_LIST,aq,clicked_details);
    quick_action_tile(actions,"Hardware",LV_SYMBOL_IMAGE,aq,clicked_details);
    quick_action_tile(actions,"Discos",LV_SYMBOL_DRIVE,aq,clicked_details);
    quick_action_tile(actions,"Reparo do Windows",LV_SYMBOL_SETTINGS,aq,NULL);
    quick_action_tile(actions,"Backup de Drivers",LV_SYMBOL_DOWNLOAD,aq,NULL);
    quick_action_tile(actions,"Exportar Relatorio",LV_SYMBOL_FILE,aq,NULL);

    lv_obj_t *modules=section(content,"Modulos de Diagnostico",210);
    lv_obj_set_width(modules,lv_pct(100));
    lv_obj_t *modulegrid=box(modules,C_PANEL,0,0);
    lv_obj_set_size(modulegrid,lv_pct(100),166);
    lv_obj_set_style_bg_opa(modulegrid,LV_OPA_TRANSP,0);
    flex(modulegrid,LV_FLEX_FLOW_ROW_WRAP,10);
    int mcols=mainw>=800?3:2;
    int mw=(mainw-24-10*(mcols-1))/mcols;
    module_item(modulegrid,mw,LV_SYMBOL_DRIVE,"Discos e particoes","Inventario coletado",true);
    module_item(modulegrid,mw,LV_SYMBOL_CHARGE,"SMART / armazenamento","Em desenvolvimento",false);
    module_item(modulegrid,mw,LV_SYMBOL_SETTINGS,"EFI / BCD","Em desenvolvimento",false);
    module_item(modulegrid,mw,LV_SYMBOL_FILE,"Arquivos Windows","Em desenvolvimento",false);
    module_item(modulegrid,mw,LV_SYMBOL_DIRECTORY,"Registro e drivers","Em desenvolvimento",false);
    module_item(modulegrid,mw,LV_SYMBOL_SAVE,"Relatorio tecnico","Em desenvolvimento",false);
    inventory(content,hw);

    /* Local SSH diagnosis without unlocking a shell or weakening auth. */
    s_ssh_diagnostics_panel=section(content,"Rede | Diagnostico SSH",166);
    lv_obj_set_width(s_ssh_diagnostics_panel,lv_pct(100));
    s_ssh_diag_state=txt(s_ssh_diagnostics_panel,"Verificando SSH...",14,C_WHITE);
    s_ssh_diag_reason=txt(s_ssh_diagnostics_panel,"Verificando pendrive...",14,C_AMBER);
    s_ssh_diag_fingerprint=txt(s_ssh_diagnostics_panel,
                               "Identidade SSH: aguardando",14,C_CYAN);
    txt(s_ssh_diagnostics_panel,
        "Somente leitura | chave privada nunca e exibida | confira o SHA256 no Windows",14,C_MUTED);

    s_notice=txt(content,"Somente leitura | Windows nao confirmado apenas por NTFS. Nenhum reparo foi executado.",14,C_MUTED);
    lv_obj_set_width(s_notice,lv_pct(100));
    if(side)sidebar(side,compact);
    redeti_input_start(display,s_group,s_input_state,s_input_detail,s_input_dot);
    update_connections(NULL);
    lv_timer_create(update_connections,3000,NULL);
}
