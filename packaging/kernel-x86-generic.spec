#
# Spec written for Tizen Mobile, some bits and pieces originate
# from MeeGo/Moblin/Fedora
#

%define upstream_version 3.12.4
%define variant x86-generic
%define kernel_version %{version}-%{release}
%define kernel_full_version %{version}-%{release}-%{variant}
%define arch_32bits i386 i586 i686 %{ix86}

%ifarch %{arch_32bits}
%define kernel_arch i386
%endif

%ifarch x86_64
%define kernel_arch x86_64
%endif

%define kernel_arch_subdir arch/x86

Name: kernel-%{variant}
Summary: The Linux kernel
Group: System/Kernel
License: GPL-2.0
URL: http://www.kernel.org/
Version: %{upstream_version}

# The below is used when we are on an -rc version
#%#define rc_num 6
#%#define release_ver 0
#%#define rc_str %{?rc_num:0.rc%{rc_num}}%{!?rc_num:1}
#%if ! 0%{?opensuse_bs}
#Release: %{rc_str}.%{release_ver}.0.0
#%else
#Release: %{rc_str}.%{release_ver}.<CI_CNT>.<B_CNT>
#%endif
Release: 1

BuildRequires: module-init-tools
BuildRequires: findutils
BuildRequires: libelf-devel
BuildRequires: binutils-devel
BuildRequires: which
BuildRequires: bc
# net-tools provides the 'hostname' utility which kernel build wants
BuildRequires: net-tools
# The below is required for building perf
BuildRequires: flex
BuildRequires: bison
BuildRequires: libdw-devel
BuildRequires: python-devel
ExclusiveArch: %{arch_32bits} x86_64

Provides: kernel = %{version}-%{release}
Provides: kernel-uname-r = %{kernel_full_version}
Requires(post): /usr/bin/ln
Requires(post): /usr/bin/sort
Requires(post): rpm

Requires(post): /usr/sbin/depmod
Requires(post): /usr/bin/dracut
Requires(post): /usr/bin/kmod

Requires(postun): /usr/bin/ln
Requires(postun): /usr/bin/sed
Requires(postun): rpm

# We can't let RPM do the dependencies automatic because it'll then pick up
# a correct but undesirable perl dependency from the module headers which
# isn't required for the kernel proper to function
AutoReq: no
AutoProv: yes

Source0: %{name}-%{version}.tar.bz2


%description
This package contains the Tizen Generic Linux kernel


%package devel
Summary: Development package for building kernel modules to match the %{variant} kernel
Group: Development/System
Provides: kernel-devel = %{kernel_full_version}
Provides: kernel-devel-uname-r = %{kernel_full_version}
Requires(post): /usr/bin/find
Requires: %{name} = %{version}-%{release}
AutoReqProv: no

%description devel
This package provides kernel headers and makefiles sufficient to build modules
against the %{variant} kernel package.


%package -n perf
Summary: The 'perf' performance counter tool
Group: System/Kernel
Provides: perf = %{kernel_full_version}
Requires: %{name} = %{version}-%{release}

%description -n perf
This package provides the "perf" tool that can be used to monitor performance
counter events as well as various kernel internal events.



###
### PREP
###
%prep
# Unpack the kernel tarbal
%setup -q -n %{name}-%{version}



###
### BUILD
###
%build
# Make sure EXTRAVERSION says what we want it to say
sed -i "s/^EXTRAVERSION.*/EXTRAVERSION = -%{release}-%{variant}/" Makefile

# Build perf
make -s -C tools/lib/traceevent ARCH=%{kernel_arch} %{?_smp_mflags}
make -s -C tools/perf WERROR=0 ARCH=%{kernel_arch}

# Build kernel and modules
%ifarch %{arch_32bits}
make -s ARCH=%{kernel_arch} generic_x86_defconfig
%endif

%ifarch x86_64
make -s ARCH=%{kernel_arch} generic_x86_64_defconfig
%endif

make -s ARCH=%{kernel_arch} %{?_smp_mflags} bzImage
make -s ARCH=%{kernel_arch} %{?_smp_mflags} modules



###
### INSTALL
###
%install
install -d %{buildroot}/boot

install -m 644 .config %{buildroot}/boot/config-%{kernel_full_version}
install -m 644 System.map %{buildroot}/boot/System.map-%{kernel_full_version}
install -m 755 %{kernel_arch_subdir}/boot/bzImage %{buildroot}/boot/vmlinuz-%{kernel_full_version}
# Dummy initrd, will not be included in the actual package but needed for files
touch %{buildroot}/boot/initrd-%{kernel_full_version}.img

make -s ARCH=%{kernel_arch} INSTALL_MOD_PATH=%{buildroot} modules_install KERNELRELEASE=%{kernel_full_version}
make -s ARCH=%{kernel_arch} INSTALL_MOD_PATH=%{buildroot} vdso_install KERNELRELEASE=%{kernel_full_version}
rm -rf %{buildroot}/lib/firmware

# And save the headers/makefiles etc for building modules against
#
# This all looks scary, but the end result is supposed to be:
# * all arch relevant include/ files
# * all Makefile/Kconfig files
# * all script/ files

# Remove existing build/source links and create pristine dirs
rm %{buildroot}/lib/modules/%{kernel_full_version}/build
rm %{buildroot}/lib/modules/%{kernel_full_version}/source
install -d %{buildroot}/lib/modules/%{kernel_full_version}/build
ln -s build %{buildroot}/lib/modules/%{kernel_full_version}/source

# First, copy all dirs containing Makefile of Kconfig files
cp --parents `find  -type f -name "Makefile*" -o -name "Kconfig*"` %{buildroot}/lib/modules/%{kernel_full_version}/build
install Module.symvers %{buildroot}/lib/modules/%{kernel_full_version}/build/
install System.map %{buildroot}/lib/modules/%{kernel_full_version}/build/

# Then, drop all but the needed Makefiles/Kconfig files
rm -rf %{buildroot}/lib/modules/%{kernel_full_version}/build/Documentation
rm -rf %{buildroot}/lib/modules/%{kernel_full_version}/build/scripts
rm -rf %{buildroot}/lib/modules/%{kernel_full_version}/build/include

# Copy config and scripts
install .config %{buildroot}/lib/modules/%{kernel_full_version}/build/
cp -a scripts %{buildroot}/lib/modules/%{kernel_full_version}/build
if [ -d %{kernel_arch_subdir}/scripts ]; then
    cp -a %{kernel_arch_subdir}/scripts %{buildroot}/lib/modules/%{kernel_full_version}/build/%{kernel_arch_subdir}/ || :
fi
if [ -f %{kernel_arch_subdir}/*lds ]; then
    cp -a %{kernel_arch_subdir}/*lds %{buildroot}/lib/modules/%{kernel_full_version}/build/%{kernel_arch_subdir}/ || :
fi
rm -f %{buildroot}/lib/modules/%{kernel_full_version}/build/scripts/*.o
rm -f %{buildroot}/lib/modules/%{kernel_full_version}/build/scripts/*/*.o
cp -a --parents %{kernel_arch_subdir}/include %{buildroot}/lib/modules/%{kernel_full_version}/build

# Copy include files
mkdir -p %{buildroot}/lib/modules/%{kernel_full_version}/build/include
find include/ -mindepth 1 -maxdepth 1 -type d | xargs -I{} cp -a {} %{buildroot}/lib/modules/%{kernel_full_version}/build/include

# Save the vmlinux file for kernel debugging into the devel package
cp vmlinux %{buildroot}/lib/modules/%{kernel_full_version}

# Mark modules executable so that strip-to-file can strip them
find %{buildroot}/lib/modules/%{kernel_full_version} -name "*.ko" -type f | xargs --no-run-if-empty chmod 755

# Move the devel headers out of the root file system
install -d %{buildroot}/usr/src/kernels
mv %{buildroot}/lib/modules/%{kernel_full_version}/build %{buildroot}/usr/src/kernels/%{kernel_full_version}

ln -sf /usr/src/kernels/%{kernel_full_version} %{buildroot}/lib/modules/%{kernel_full_version}/build

# Install perf
install -d %{buildroot}
make -s -C tools/perf DESTDIR=%{buildroot} install
install -d  %{buildroot}/usr/bin
install -d  %{buildroot}/usr/libexec
mv %{buildroot}/bin/* %{buildroot}/usr/bin/
mv %{buildroot}/libexec/* %{buildroot}/usr/libexec/
rm %{buildroot}/etc/bash_completion.d/perf



###
### SCRIPTS
###

%post
if [ -f "/boot/loader/loader.conf" ]; then
	# EFI boot with gummiboot
	INSTALLERFW_MOUNT_PREFIX="/" /usr/sbin/setup-gummiboot-conf
else
	# Legacy boot
	last_installed_ver="$(rpm -q --qf '%{INSTALLTIME}: %{VERSION}-%{RELEASE}\n' kernel-%{variant} | sort -r | sed -e 's/[^:]*: \(.*\)/\1/g' | sed -n -e "1p")"
	ln -sf vmlinuz-$last_installed_ver-%{variant} /boot/vmlinuz

	if [ -z "$last_installed_ver" ]; then
		# Something went wrong, print some diagnostics
		printf "%s\n" "Error: cannot find kernel version" 1>&2
		printf "%s\n" "The command was: rpm -q --qf '%{INSTALLTIME}: %{VERSION}-%{RELEASE}\n' kernel-%{variant} | sort -r | sed -e 's/[^:]*: \(.*\)/\1/g' | sed -n -e \"1p\"" 1>&2
		printf "%s\n" "Output of the \"rpm -q --qf '%{INSTALLTIME}: %{VERSION}-%{RELEASE}\n' kernel-%{variant}\" is:" 1>&2
		result="$(rpm -q --qf '%{INSTALLTIME}: %{VERSION}-%{RELEASE}\n' kernel-%{variant})"
		printf "%s\n" "$result" 1>&2
	fi
fi

/usr/bin/dracut /boot/initrd-%{kernel_full_version}.img %{kernel_full_version}

%post devel
if [ -x /usr/sbin/hardlink ]; then
	cd /usr/src/kernels/%{kernel_full_version}
	/usr/bin/find . -type f | while read f; do
		hardlink -c /usr/src/kernels/*/$f $f
	done
fi

%postun
if [ -f "/boot/loader/loader.conf" ]; then
	# EFI boot with gummiboot
	INSTALLERFW_MOUNT_PREFIX="/" /usr/sbin/setup-gummiboot-conf
else
	last_installed_ver="$(rpm -q --qf '%{INSTALLTIME}: %{VERSION}-%{RELEASE}\n' kernel-%{variant} | sort -r | sed -e 's/[^:]*: \(.*\)/\1/g' | sed -n -e "1p")"
	if [ -n "$last_installed_ver" ]; then
		ln -sf vmlinuz-$last_installed_ver-%{variant} /boot/vmlinuz
	else
		rm -rf /boot/vmlinuz
	fi
fi



###
### FILES
###
%files
%license COPYING
/boot/vmlinuz-%{kernel_full_version}
/boot/System.map-%{kernel_full_version}
/boot/config-%{kernel_full_version}
%dir /lib/modules/%{kernel_full_version}
/lib/modules/%{kernel_full_version}/kernel
/lib/modules/%{kernel_full_version}/build
/lib/modules/%{kernel_full_version}/source
/lib/modules/%{kernel_full_version}/vdso
/lib/modules/%{kernel_full_version}/modules.*
%ghost /boot/initrd-%{kernel_full_version}.img


%files devel
%license COPYING
%verify(not mtime) /usr/src/kernels/%{kernel_full_version}
/lib/modules/%{kernel_full_version}/vmlinux


%files -n perf
%license COPYING
/usr/bin/perf
/usr/libexec/perf-core
