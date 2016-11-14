#	pdfminify - Tool to minify PDF files.
#	Copyright (C) 2016-2016 Johannes Bauer
#
#	This file is part of pdfminify.
#
#	pdfminify is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	pdfminify is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with pdfminify; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>
#

from .PDFFilter import PDFFilter
from llpdf.img.PDFImage import PDFImageType
from llpdf.types.PDFObject import PDFObject
from llpdf.types.PDFName import PDFName
from llpdf.interpreter.GraphicsInterpreter import GraphicsInterpreter

class DownscaleImageOptimization(PDFFilter):
	def _draw_callback(self, draw_cmd):
		image_xref = draw_cmd.image_obj.xref
		(w, h) = (abs(draw_cmd.extents.width), abs(draw_cmd.extents.height))
		if image_xref in self._max_image_extents:
			(current_w, current_h) = self._max_image_extents[image_xref]
			w = max(w, current_w)
			h = max(h, current_h)
		self._max_image_extents[image_xref] = (w, h)

	def _rescale(self, image_obj, scale_factor):
		img = image_obj.get_image()

		if (img.imgtype == PDFImageType.FlateDecode) and (self._args.jpg_images):
			target_type = img.imgtype
		else:
			target_type = img.imgtype
		if self._args.verbose:
			print("Resampling %s to %s with scale factor %.2f" % (img, target_type.name, scale_factor))
		img = img.reformat(target_type, scale_factor = scale_factor)
		new_obj = PDFObject.create_image(image_obj.objid, image_obj.gennum, img)
		self._optimized(len(image_obj), len(new_obj))
		image_obj.replace_by(new_obj)

	def run(self):
		self._max_image_extents = { }

		# Run through pages first to determine image extents
		for (page_obj, page_content) in self._pdf.parsed_pages:
			interpreter = GraphicsInterpreter(pdf_lookup = self._pdf, page_obj = page_obj)
			interpreter.set_draw_callback(self._draw_callback)
			interpreter.run(page_content)

		for (img_xref, (maxw_mm, maxh_mm)) in self._max_image_extents.items():
			image = self._pdf.lookup(img_xref)
			if (PDFName("/Width") not in image.content):
				# TODO: What kind of image doesn't have width/height set?
				continue
			(pixel_w, pixel_h) = (image.content[PDFName("/Width")], image.content[PDFName("/Height")])

			maxw_inches = maxw_mm / 25.4
			maxh_inches = maxh_mm / 25.4
			current_dpi_w = pixel_w / maxw_inches
			current_dpi_h = pixel_h / maxh_inches
			current_dpi = min(current_dpi_w, current_dpi_h)
			if self._args.verbose:
				print("Current DPI of %s: %.0f" % (image, current_dpi))

			scale_factor = min(self._args.target_dpi / current_dpi, 1)
			self._rescale(image, scale_factor)
