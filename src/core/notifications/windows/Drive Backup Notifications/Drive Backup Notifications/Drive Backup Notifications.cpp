#include "wintoastlib.h"
#include <string>
#include <windows.h>

using namespace WinToastLib;

class CustomHandler : public IWinToastHandler {
public:
    void toastActivated() const {}

    void toastActivated(int) const {}

    void toastDismissed(WinToastDismissalReason) const {}

    void toastFailed() const {}
};

enum Results {
    ToastShown,               // toast was shown successfully
    ToastClicked,             // user clicked on the toast
    ToastDismissed,           // user dismissed the toast
    ToastTimeOut,             // toast timed out
    ToastHided,               // application hid the toast
    ToastNotActivated,        // toast was not activated
    ToastFailed,              // toast failed
    SystemNotSupported,       // system does not support toasts
    UnhandledOption,          // unhandled option
    MultipleTextNotSupported, // multiple texts were provided
    InitializationFailure,    // toast notification manager initialization failure
    ToastNotLaunched          // toast could not be launched
};

#define COMMAND_ACTION     L"--action"
#define COMMAND_AUMI       L"--aumi"
#define COMMAND_APPNAME    L"--appname"
#define COMMAND_APPID      L"--appid"
#define COMMAND_EXPIREMS   L"--expirems"
#define COMMAND_TEXT       L"--text"
#define COMMAND_HELP       L"--help"
#define COMMAND_IMAGE      L"--image"
#define COMMAND_SHORTCUT   L"--only-create-shortcut"
#define COMMAND_AUDIOSTATE L"--audio-state"
#define COMMAND_ATTRIBUTE  L"--attribute"

#define COMMAND_TITLE L"--title"
#define COMMAND_BODY  L"--body"

int wmain(int argc, LPWSTR* argv) {
    if (!WinToast::isCompatible()) {
        return Results::SystemNotSupported;
    }

    std::wstring appName        = L"Drive Backup";
    std::wstring appUserModelID = WinToast::configureAUMI(L"geoh2os8295", L"drive-backup", L"notifications", L"1.0");
    std::wstring title          = L"Drive Backup Notifications";
    std::wstring body           = L"Notification";
    std::wstring imagePath      = L"";

    WinToastTemplate::AudioOption audioOption = WinToastTemplate::AudioOption::Default;

    int i;
    for (i = 1; i < argc; i++) {
        if (!wcscmp(COMMAND_IMAGE, argv[i])) {
            imagePath = argv[++i];
        } else if (!wcscmp(COMMAND_APPNAME, argv[i])) {
            appName = argv[++i];
        } else if (!wcscmp(COMMAND_AUMI, argv[i]) || !wcscmp(COMMAND_APPID, argv[i])) {
            appUserModelID = argv[++i];
        } else if (!wcscmp(COMMAND_TITLE, argv[i])) {
            title = argv[++i];
        } else if (!wcscmp(COMMAND_BODY, argv[i])) {
            body = argv[++i];
        } else {
            std::wcerr << L"Option not recognized: " << argv[i] << std::endl;
            return Results::UnhandledOption;
        }
    }

    WinToast::instance()->setAppName(appName);
    WinToast::instance()->setAppUserModelId(appUserModelID);

    if (!WinToast::instance()->initialize()) {
        return Results::InitializationFailure;
    }

    WinToastTemplate templ(WinToastTemplate::ImageAndText02);
    templ.setTextField(title, WinToastTemplate::FirstLine);
    templ.setTextField(body, WinToastTemplate::SecondLine);
    templ.setAudioOption(audioOption);
    templ.setImagePath(imagePath);

    if (WinToast::instance()->showToast(templ, new CustomHandler()) < 0) {
        return Results::ToastFailed;
    }

    Sleep(15000);

    return Results::ToastShown;
}
