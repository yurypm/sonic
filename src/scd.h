/*
 * Copyright (C) 2010-2016 Arista Networks, Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

// scd linux kernel driver public definitions

// Allow an ardma handler set to be registered.
struct scd_ardma_ops {
   void (*probe)(struct pci_dev *pdev, void *scdregs,
      unsigned long ardma_offset,
      void *localbus,
      unsigned long interrupt_mask_ardma,
      unsigned long interrupt_mask_read_offset,
      unsigned long interrupt_mask_set_offset,
      unsigned long interrupt_mask_clear_offset);
   void (*remove)(struct pci_dev *pdev);
   void (*shutdown)(struct pci_dev *pdev);
   bool (*interrupt)(struct pci_dev *pdev);
};

// Allow scd-em callbacks to be registered
struct scd_em_ops {
   void (*probe)(struct pci_dev *pdev);
   void (*remove)(struct pci_dev *pdev);
};

// Allow scd-sonic callbacks to be registered
struct scd_sonic_ops {
   void (*probe)(struct pci_dev *pdev);
   void (*remove)(struct pci_dev *pdev);
   void (*init_trigger)(struct pci_dev *pdev);
};

int scd_register_ardma_ops(struct scd_ardma_ops *ops);
void scd_unregister_ardma_ops(void);
int scd_register_em_ops(struct scd_em_ops *ops);
void scd_unregister_em_ops(void);
int scd_register_sonic_ops(struct scd_sonic_ops *ops);
void scd_unregister_sonic_ops(void);
struct pci_dev *scd_get_pdev(const char *name);
u32 scd_read_register(struct pci_dev *pdev, u32 offset);
void scd_write_register(struct pci_dev *pdev, u32 offset, u32 val);
u64 scd_ptp_timestamp(void);

// Copyright (c) 2010-2016 Arista Networks, Inc.  All rights reserved.
// Arista Networks, Inc. Confidential and Proprietary.
