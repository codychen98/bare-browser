.class public Lorg/barebrowser/fork/SnackbarSettingsActivity;
.super Landroid/app/Activity;
.source "SnackbarSettingsActivity.java"


# instance fields
.field private fullscreenBox:Landroid/widget/CheckBox;

.field private undoBox:Landroid/widget/CheckBox;


# direct methods
.method public constructor <init>()V
    .registers 1

    invoke-direct {p0}, Landroid/app/Activity;-><init>()V

    return-void
.end method

.method static synthetic access$000(Lorg/barebrowser/fork/SnackbarSettingsActivity;)Landroid/widget/CheckBox;
    .registers 1

    iget-object p0, p0, Lorg/barebrowser/fork/SnackbarSettingsActivity;->fullscreenBox:Landroid/widget/CheckBox;

    return-object p0
.end method

.method static synthetic access$100(Lorg/barebrowser/fork/SnackbarSettingsActivity;)Landroid/widget/CheckBox;
    .registers 1

    iget-object p0, p0, Lorg/barebrowser/fork/SnackbarSettingsActivity;->undoBox:Landroid/widget/CheckBox;

    return-object p0
.end method


# virtual methods
.method protected onCreate(Landroid/os/Bundle;)V
    .registers 10

    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V

    const-string v0, "bare_fork_snackbars"

    const/4 v1, 0x0

    invoke-virtual {p0, v0, v1}, Lorg/barebrowser/fork/SnackbarSettingsActivity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    new-instance v2, Landroid/widget/LinearLayout;

    invoke-direct {v2, p0}, Landroid/widget/LinearLayout;-><init>(Landroid/content/Context;)V

    const/4 v3, 0x1

    invoke-virtual {v2, v3}, Landroid/widget/LinearLayout;->setOrientation(I)V

    const/16 v3, 0x30

    invoke-virtual {v2, v3, v3, v3, v3}, Landroid/widget/LinearLayout;->setPadding(IIII)V

    new-instance v3, Landroid/widget/TextView;

    invoke-direct {v3, p0}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V

    const-string v4, "Bare fork snackbar options"

    invoke-virtual {v3, v4}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    const/high16 v4, 0x41a00000    # 20.0f

    invoke-virtual {v3, v4}, Landroid/widget/TextView;->setTextSize(F)V

    invoke-virtual {v2, v3}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    new-instance v3, Landroid/widget/TextView;

    invoke-direct {v3, p0}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V

    const-string v4, "Defaults match official Bare. Enable a switch to hide that notice."

    invoke-virtual {v3, v4}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    invoke-virtual {v2, v3}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    new-instance v3, Landroid/widget/CheckBox;

    invoke-direct {v3, p0}, Landroid/widget/CheckBox;-><init>(Landroid/content/Context;)V

    iput-object v3, p0, Lorg/barebrowser/fork/SnackbarSettingsActivity;->fullscreenBox:Landroid/widget/CheckBox;

    const-string v4, "Hide fullscreen exit notice"

    invoke-virtual {v3, v4}, Landroid/widget/CheckBox;->setText(Ljava/lang/CharSequence;)V

    const-string v4, "hide_fullscreen_exit"

    invoke-interface {v0, v4, v1}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z

    move-result v4

    invoke-virtual {v3, v4}, Landroid/widget/CheckBox;->setChecked(Z)V

    invoke-virtual {v2, v3}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    new-instance v3, Landroid/widget/CheckBox;

    invoke-direct {v3, p0}, Landroid/widget/CheckBox;-><init>(Landroid/content/Context;)V

    iput-object v3, p0, Lorg/barebrowser/fork/SnackbarSettingsActivity;->undoBox:Landroid/widget/CheckBox;

    const-string v4, "Hide tab-close Undo bar"

    invoke-virtual {v3, v4}, Landroid/widget/CheckBox;->setText(Ljava/lang/CharSequence;)V

    const-string v4, "hide_tab_close_undo"

    invoke-interface {v0, v4, v1}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z

    move-result v1

    invoke-virtual {v3, v1}, Landroid/widget/CheckBox;->setChecked(Z)V

    invoke-virtual {v2, v3}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    new-instance v1, Landroid/widget/Button;

    invoke-direct {v1, p0}, Landroid/widget/Button;-><init>(Landroid/content/Context;)V

    const-string v3, "Save"

    invoke-virtual {v1, v3}, Landroid/widget/Button;->setText(Ljava/lang/CharSequence;)V

    new-instance v3, Lorg/barebrowser/fork/SnackbarSettingsActivity$1;

    invoke-direct {v3, p0, v0}, Lorg/barebrowser/fork/SnackbarSettingsActivity$1;-><init>(Lorg/barebrowser/fork/SnackbarSettingsActivity;Landroid/content/SharedPreferences;)V

    invoke-virtual {v1, v3}, Landroid/widget/Button;->setOnClickListener(Landroid/view/View$OnClickListener;)V

    invoke-virtual {v2, v1}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V

    invoke-virtual {p0, v2}, Lorg/barebrowser/fork/SnackbarSettingsActivity;->setContentView(Landroid/view/View;)V

    return-void
.end method
