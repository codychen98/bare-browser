.class Lorg/barebrowser/fork/SnackbarSettingsActivity$1;
.super Ljava/lang/Object;
.source "SnackbarSettingsActivity.java"

# interfaces
.implements Landroid/view/View$OnClickListener;


# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lorg/barebrowser/fork/SnackbarSettingsActivity;->onCreate(Landroid/os/Bundle;)V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation


# instance fields
.field final synthetic this$0:Lorg/barebrowser/fork/SnackbarSettingsActivity;

.field final synthetic val$prefs:Landroid/content/SharedPreferences;


# direct methods
.method constructor <init>(Lorg/barebrowser/fork/SnackbarSettingsActivity;Landroid/content/SharedPreferences;)V
    .registers 3

    iput-object p1, p0, Lorg/barebrowser/fork/SnackbarSettingsActivity$1;->this$0:Lorg/barebrowser/fork/SnackbarSettingsActivity;

    iput-object p2, p0, Lorg/barebrowser/fork/SnackbarSettingsActivity$1;->val$prefs:Landroid/content/SharedPreferences;

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method


# virtual methods
.method public onClick(Landroid/view/View;)V
    .registers 5

    iget-object v0, p0, Lorg/barebrowser/fork/SnackbarSettingsActivity$1;->val$prefs:Landroid/content/SharedPreferences;

    invoke-interface {v0}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    iget-object v1, p0, Lorg/barebrowser/fork/SnackbarSettingsActivity$1;->this$0:Lorg/barebrowser/fork/SnackbarSettingsActivity;

    invoke-static {v1}, Lorg/barebrowser/fork/SnackbarSettingsActivity;->access$000(Lorg/barebrowser/fork/SnackbarSettingsActivity;)Landroid/widget/CheckBox;

    move-result-object v1

    invoke-virtual {v1}, Landroid/widget/CheckBox;->isChecked()Z

    move-result v1

    const-string v2, "hide_fullscreen_exit"

    invoke-interface {v0, v2, v1}, Landroid/content/SharedPreferences$Editor;->putBoolean(Ljava/lang/String;Z)Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    iget-object v1, p0, Lorg/barebrowser/fork/SnackbarSettingsActivity$1;->this$0:Lorg/barebrowser/fork/SnackbarSettingsActivity;

    invoke-static {v1}, Lorg/barebrowser/fork/SnackbarSettingsActivity;->access$100(Lorg/barebrowser/fork/SnackbarSettingsActivity;)Landroid/widget/CheckBox;

    move-result-object v1

    invoke-virtual {v1}, Landroid/widget/CheckBox;->isChecked()Z

    move-result v1

    const-string v2, "hide_tab_close_undo"

    invoke-interface {v0, v2, v1}, Landroid/content/SharedPreferences$Editor;->putBoolean(Ljava/lang/String;Z)Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    invoke-interface {v0}, Landroid/content/SharedPreferences$Editor;->apply()V

    iget-object v0, p0, Lorg/barebrowser/fork/SnackbarSettingsActivity$1;->this$0:Lorg/barebrowser/fork/SnackbarSettingsActivity;

    const-string v1, "Saved"

    const/4 v2, 0x0

    invoke-static {v0, v1, v2}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;

    move-result-object v0

    invoke-virtual {v0}, Landroid/widget/Toast;->show()V

    iget-object v0, p0, Lorg/barebrowser/fork/SnackbarSettingsActivity$1;->this$0:Lorg/barebrowser/fork/SnackbarSettingsActivity;

    invoke-virtual {v0}, Lorg/barebrowser/fork/SnackbarSettingsActivity;->finish()V

    return-void
.end method
